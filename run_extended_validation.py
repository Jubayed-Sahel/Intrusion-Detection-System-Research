"""Evaluate saved models on uncapped sources and locked GeNIS models on OCPP."""
import argparse
import json
import zipfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.utils.class_weight import compute_sample_weight

import run_source_holdout as source
from src.xai_ids.benchmark import TabularPreprocessor, make_model, sha256
from src.xai_ids.recent_data import _hex_numeric, connection_groups

OUT = Path("outputs/extended_validation_20261108")
PROTOCOL = Path("EXTENDED_VALIDATION_PROTOCOL.md")


def scores(matrix, classes):
    matrix = np.asarray(matrix)
    tp = matrix.diagonal()
    support = matrix.sum(axis=1)
    pred = matrix.sum(axis=0)
    f1 = np.divide(2*tp, support+pred, out=np.zeros(len(tp)), where=(support+pred)>0)
    result = dict(test_rows=int(support.sum()), accuracy=float(tp.sum()/support.sum()),
                  macro_f1=float(f1[support>0].mean()))
    if classes == ["Attack", "Normal"]:
        result.update(attacks=int(support[0]), benign=int(support[1]),
                      missed=int(matrix[0,1]), false_alarms=int(matrix[1,0]),
                      attack_recall=float(tp[0]/support[0]) if support[0] else None,
                      fpr=float(matrix[1,0]/support[1]) if support[1] else None)
    return result


def uncapped(dataset=None):
    folds, frames, provenance = source.prepare_folds()
    inputs = {}
    results, coverage, confusions = [], [], []
    out = OUT / ("uncapped_" + dataset if dataset else "uncapped")
    out.mkdir(parents=True, exist_ok=True)
    signature = {"runner":sha256(Path(__file__)), "protocol":sha256(PROTOCOL),
                 "source_manifest":sha256(source.OUT/"run_manifest.json"),"dataset":dataset}
    prior = out/"protocol_hashes.json"
    if prior.exists() and json.loads(prior.read_text()) != signature:
        raise ValueError("Uncapped checkpoint belongs to different code or protocol")
    prior.write_text(json.dumps(signature,indent=2))
    archive = Path("data/official/14919237/3-scenarios.zip")
    with zipfile.ZipFile(archive) as z:
        for fold in folds:
            d = fold["dataset"]
            if dataset and d != dataset: continue
            foldno = fold["fold"]
            common = dict(dataset=d,fold=foldno)
            checkpoint = out/f"{d}_{foldno}.json"
            if checkpoint.exists():
                saved = json.loads(checkpoint.read_text())
                results.extend(saved["results"]); coverage.extend(saved["coverage"]); confusions.extend(saved["confusions"])
                inputs.update(saved["inputs"]); continue
            print(d,foldno,flush=True)
            start = (len(results),len(coverage),len(confusions))
            train,_,_ = source.partition(frames[d], fold["test_sources"])
            training_groups = set(train["__group"])
            raw_classes = sorted(provenance[d]["source_label_counts"].keys() - {"Unknown"})
            models = {}
            for task in ("binary","multiclass"):
                for name in ("random_forest","xgboost"):
                    context = source.context_name(fold,task,name)
                    path = source.OUT/"models"/(context+".joblib")
                    digest = sha256(path)
                    saved = json.loads((source.OUT/"contexts"/context/"predictive_complete.json").read_text())
                    if digest != saved["model_sha256"]:
                        raise ValueError("Model checkpoint hash mismatch")
                    inputs[path.as_posix()] = digest
                    artifact=joblib.load(path)
                    artifact["model"].set_params(n_jobs=4)
                    labels = ["Attack","Normal"] if task=="binary" else raw_classes
                    models[task,name] = (artifact,labels,np.zeros((len(labels),len(labels)),dtype=np.int64))
            features = sorted(set().union(*(set(a["preprocessor"].feature_names) for a,_,_ in models.values())))
            genis = d=="GeNIS2025"
            label = "CategoryLabel" if genis else "label"
            group_fields = ["FlowID"] if genis else ["ip.src","ip.dst","ip.proto","tcp.srcport","tcp.dstport","udp.srcport","udp.dstport"]
            known_hashes={r["member"]:r["sha256"] for r in provenance[d]["source_files"]}
            for member in fold["test_sources"]:
                import hashlib
                opener = (lambda: z.open(member)) if genis else (lambda: (Path("data/official/14502760")/member).open("rb"))
                digest=hashlib.sha256()
                with opener() as f:
                    while block:=f.read(1<<20): digest.update(block)
                if digest.hexdigest()!=known_hashes[member]:
                    raise ValueError(f"Author file changed: {member}")
                inputs[member]=digest.hexdigest()
                count = dict(**common,source=member,raw=0,unknown=0,group_excluded=0,eligible=0)
                with opener() as f:
                    for chunk in pd.read_csv(f,usecols=sorted(set(features+[label]+group_fields)),chunksize=100000,low_memory=False):
                        count["raw"]+=len(chunk)
                        y=chunk[label].astype("string").str.strip()
                        if y.isna().any() or not set(y) <= set(raw_classes)|({"Unknown"} if not genis else set()):
                            raise ValueError("Unexpected raw label")
                        g=chunk.FlowID.astype(str) if genis else connection_groups(chunk)
                        known=~y.eq("Unknown"); overlap=g.isin(training_groups)
                        count["unknown"]+=int((~known).sum())
                        count["group_excluded"]+=int((known&overlap).sum())
                        keep=known&~overlap
                        count["eligible"]+=int(keep.sum())
                        if not keep.any():continue
                        frame=chunk.loc[keep,features].copy()
                        for col in features:
                            if col in source_feature_categories(genis):
                                frame[col]=frame[col].astype("string")
                            else:
                                frame[col]=pd.to_numeric(frame[col] if genis or pd.api.types.is_numeric_dtype(frame[col]) else _hex_numeric(frame[col]),errors="coerce")
                        y=y[keep].to_numpy(dtype=str)
                        for (task,name),(a,labels,matrix) in models.items():
                            actual=np.where(np.char.lower(y)=="benign","Normal","Attack") if task=="binary" else y
                            pred=np.asarray(a["classes"])[a["model"].predict(a["preprocessor"].transform(frame)).astype(int)]
                            # Dense counts on fixed vocabularies, including test-only labels.
                            index={l:i for i,l in enumerate(labels)}
                            codes=pd.Series(actual).map(index).to_numpy(dtype=int)*len(labels)+pd.Series(pred).map(index).to_numpy(dtype=int)
                            matrix+=np.bincount(codes,minlength=matrix.size).reshape(matrix.shape)
                if count["raw"]!=count["unknown"]+count["group_excluded"]+count["eligible"]:
                    raise ValueError("Raw row accounting failed")
                coverage.append(count)
                print(member,count["eligible"],flush=True)
            for (task,name),(a,labels,matrix) in models.items():
                fields={**common,"task":task,"model":name}
                results.append({**fields,**scores(matrix,labels),
                   "unseen_label_test_rows":int(sum(matrix[i].sum() for i,l in enumerate(labels) if l not in a["classes"]))})
                confusions.extend({**fields,"actual":l,"predicted":p,"count":int(matrix[i,j])}
                                  for i,l in enumerate(labels) for j,p in enumerate(labels))
            checkpoint.write_text(json.dumps({"results":results[start[0]:],"coverage":coverage[start[1]:],
                  "confusions":confusions[start[2]:],"inputs":{k:v for k,v in inputs.items() if k in fold["test_sources"] or f"{d}_fold{foldno:02}" in k}},indent=2))
    for name,rows in [("metrics",results),("coverage",coverage),("confusion",confusions)]:
        pd.DataFrame(rows).to_csv(out/(name+".csv"),index=False)
    (out/"manifest.json").write_text(json.dumps({**signature,"input_hashes":inputs,
        "contexts":len(results),"sources":len(coverage),"eligible":sum(r["eligible"] for r in coverage),
        "outputs":{n:sha256(out/n) for n in ("metrics.csv","coverage.csv","confusion.csv")}},indent=2))


def source_feature_categories(genis):
    from src.xai_ids.recent_data import GENIS_CATEGORICAL,GOTHAM_CATEGORICAL
    return GENIS_CATEGORICAL if genis else GOTHAM_CATEGORICAL


def harmonize(frame, external):
    if external:
        proto=pd.to_numeric(frame.Protocol,errors="raise")
        left,right=frame["Src Port"],frame["Dst Port"]
        duration=frame["Flow Duration"]/1e6
        packets=frame["Total Fwd Packet"]+frame["Total Bwd packets"]
    else:
        proto=frame.Proto.map({"tcp":6,"udp":17,"icmp":1,"ipv6-icmp":58}).fillna(-1)
        left,right=frame.Sport,frame.Dport
        duration,packets=frame.Dur,frame.TotPkts
    proto=proto.where(proto.isin([1,6,17,58]),-1)
    transport=proto.isin([6,17])
    left=left.where(left.between(0,65535)&transport)
    right=right.where(right.between(0,65535)&transport)
    return pd.DataFrame(dict(protocol=proto.astype(int).astype(str),port_low=np.minimum(left,right),
        port_high=np.maximum(left,right),duration_s=duration.where(duration>=0),packets=packets.where(packets>0)))


def external():
    root=Path("data/official/14887131")
    file=root/"Balanced_OCPP16_TCP-IP_Layer.zip"
    ledger=json.loads((root/"acquisition.json").read_text())
    listed=next(r for r in ledger["files"] if r["filename"]==file.name)
    if not listed["checksum_verified"] or sha256(file)!=listed["sha256"]:
        raise ValueError("Official OCPP archive hash mismatch")
    source.load_primary("GeNIS2025")  # verify both prepared partitions
    train,test=(pd.read_parquet(Path("data/prepared/GeNIS2025")/name) for name in ("train.parquet","test.parquet"))
    yt=np.where(train.Label.str.lower().eq("benign"),1,0)
    config=yaml.safe_load(Path("config_recent.yaml").read_text())["models"]
    X=harmonize(train,False); G=harmonize(test,False)
    models={}
    for spec, features in (("transport",list(X.columns[:3])),("transport_volume",list(X.columns))):
        pre=TabularPreprocessor(features).fit(X)
        for name in ("random_forest","xgboost"):
            model=make_model(name,config,42,2); model.set_params(n_jobs=4)
            model.fit(pre.transform(X),yt,sample_weight=compute_sample_weight("balanced",yt) if name=="xgboost" else None)
            models[spec,name]=(pre,model)
    # Target is read and scored only after the source-only models are locked.
    with zipfile.ZipFile(file) as z:
        members=[n for n in sorted(z.namelist()) if n.endswith(("/Combined/Train.csv","/Combined/Test.csv"))]
        if len(members)!=2:raise ValueError("Unexpected OCPP Combined members")
        O=pd.concat([pd.read_csv(z.open(n)).assign(_member=n) for n in members],ignore_index=True)
    labels={"normal","cyberattack_ocpp16_fdi_chargingprofile","cyberattack_ocpp16_dos_flooding_heartbeat",
            "cyberattack_ocpp16_doc_idtag","cyberattack_ocpp16_unauthorized_access"}
    if set(O.Label)!=labels: raise ValueError("Unexpected OCPP labels")
    E=harmonize(O,True)
    out=OUT/"external";out.mkdir(parents=True,exist_ok=True)
    rows,classes=[],[]
    for (spec,name),(pre,model) in models.items():
        for dataset,x,raw,benign in (("GeNIS",G,test.Label,"benign"),("OCPP",E,O.Label,"normal")):
            act=np.where(raw.str.lower().eq(benign),"Normal","Attack")
            pred=np.asarray(["Attack","Normal"])[model.predict(pre.transform(x)).astype(int)]
            fields=dict(feature_set=spec,model=name,test=dataset)
            rows.append({**fields,**scores(confusion_matrix(act,pred,labels=["Attack","Normal"]),["Attack","Normal"])})
            for label in sorted(set(raw)):
                mask=raw.eq(label).to_numpy()
                classes.append({**fields,"label":label,"rows":int(mask.sum()),"correct":int((pred[mask]==act[mask]).sum())})
    for name,values in [("metrics",rows),("per_label",classes)]:
        pd.DataFrame(values).to_csv(out/(name+".csv"),index=False)
    (out/"manifest.json").write_text(json.dumps(dict(archive_sha256=listed["sha256"],members=members,
        rows=len(O),labels=O.Label.value_counts().to_dict(),exact_duplicate_rows=int(O.drop(columns="_member").duplicated().sum()),
        protocol_sha256=sha256(PROTOCOL),runner_sha256=sha256(Path(__file__)),geNIS_prepared={p:sha256(Path("data/prepared/GeNIS2025")/p) for p in ("train.parquet","test.parquet")},
        outputs={n:sha256(out/n) for n in ("metrics.csv","per_label.csv")}),indent=2))
    print(pd.DataFrame(rows).to_string(index=False))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=["external","GeNIS2025","Gotham2025"])
    a=p.parse_args()
    external() if a.stage=="external" else uncapped(a.stage)
