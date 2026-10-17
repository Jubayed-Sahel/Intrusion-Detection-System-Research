# Run the IDS and its explanations

Open PowerShell in `C:\Users\User\Desktop\498R`.

## Generate predictions and explanations

```powershell
.\.venv-reproduction\Scripts\python.exe run_project.py
```

This runs both saved model families on both datasets, for normal/attack detection and attack-category classification. It chooses the first labelled attack record in each prepared test set and creates eight fresh TreeSHAP explanation reports with local randomized-feature checks. It does not train new models or capture live network traffic. The output prints the prediction and whether that alert's explanation passed its evidence checks.

The final message gives a unique folder under `outputs/local_runs/`. Open its `.md` files for readable reports. Each report includes the prediction, model confidence, influential feature values, signed contributions, and explanation-check results. The companion `.json` files and `demo_summary.json` contain machine-readable outputs. `REVIEW_REQUIRED` means the explanation did not pass the strict local check; it is not a program failure or a determination that the detection itself is wrong.

For a shorter demonstration, append `--dataset GeNIS2025`. Alternatively, the convenience wrapper is `.\Run-Project.ps1` if script execution is enabled.

## Check the installation and research outputs

```powershell
.\.venv-reproduction\Scripts\python.exe run_project.py --check
```

This checks installed dependency compatibility, runs the unit tests, verifies the recent research artifacts, then generates the demonstrations. To rehash the downloaded official sources as well:

```powershell
.\.venv-reproduction\Scripts\python.exe verify_recent_benchmark.py --verify-raw
```

## Try fresh training with both explanation methods

```powershell
.\.venv-reproduction\Scripts\python.exe run_project.py --smoke-train
```

This uses the prepared GeNIS training/test split to fit four small models: Random Forest and XGBoost, each for binary and multiclass tasks. It evaluates TreeSHAP and LIME on ten matched records per model and saves a configuration, source snapshots, model files, predictions/metrics, attributions, controls, and explanation summaries in a new local-run folder.

It uses 20 Random Forest trees and 30 XGBoost estimators, instead of the larger research settings. It is an execution check, not a reproduction of the paper. The paper's complete 40-fit retraining instructions are in README.md under “Reproduce the current study.” The existing primary output folder resumes saved checkpoints, so rerunning it does not independently retrain completed models.

## Checks completed on 17 October 2026

- Syntax parsing passed for 44 active Python files across root scripts, `src`, tests, and the overview generator. Environments, backups, and archived result snapshots were excluded.
- Inspected the current preparation, preprocessing, training, SHAP/LIME evaluation, group inference, alert reporting, audit, acquisition, and verification paths. Syntax and executed checks are not an exhaustive proof that every possible input works.
- Installed dependencies are compatible; all 21 unit tests pass.
- The recent verifier passes with raw-source checks: 40 predictive fits, 24 paired explanation contexts, and eight extended audit contexts.
- Historical output verification and both expanded/clean-reproduction evidence verifiers pass.
- All eight saved current-study models generated fresh predictions and explanation reports successfully. GeNIS examples passed the local explanation gate; Gotham examples required review, which is a supported report outcome.
- A fresh small GeNIS run completed four fits and eight SHAP/LIME explanation summaries, with ten matched records per model.
- The PowerShell wrapper's help command runs successfully.

No blocking execution failure was found in these checks. Dataset-specific preparation, report assumptions, and fixed study-size validators still mean arbitrary new datasets and altered full-study designs need adaptation. Downloading again, rebuilding manuscript layouts, full historical retraining, and an independent 40-fit primary reproduction were not performed in this check. Existing primary results and frozen experiment sources were preserved.
