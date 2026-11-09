# IEEE submission preparation

**8 November 2026 update:** MIAC 2027 Track 5 is the provisional Bangladesh destination. The anonymous review candidate is five IEEEtran pages including 30 references, within its advertised six-page maximum. Build it with `python build_conference_paper.py`; source is `paper/conference/main.tex`. The extended report remains separate. The [Bangladesh submission plan](BANGLADESH_SUBMISSION_PLAN.md) records the conflicting deadline years, assistance/screening policies and other details that must be confirmed before submission. No paper has been submitted or venue-certified. The general October guidance below is retained as background; it does not replace the current conference instructions.

IEEE is the selected publishing direction, but no particular journal or conference has been selected. The current official-source study is described in [the GeNIS/Gotham manuscript](output/pdf/xai_ids_recent2025_paper.pdf), a research draft now generated with the official IEEEtran LaTeX class in conference/US Letter mode. Editable sources are in `paper/ieee/main.tex`, and the builder is `src/xai_ids/ieee_paper.py`. The class controls fonts, two columns, headings, abstract placement, margins, numbered equations, captions, and bibliography. The earlier custom ReportLab layout is no longer the default build. Section II now compares the protocol with Neupane et al., Gaspar et al., Warnecke et al., and Arreche et al. (E-XAI); claim support is recorded in [RECENT_REFERENCE_VALIDATION.md](RECENT_REFERENCE_VALIDATION.md). It uses the generic official conference class; it is not certified against a selected venue's requirements or PDF eXpress. The earlier CIC/UNSW manuscript is historical.

Official template resources rechecked on 21 October 2026:

- Conference templates: https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/
- Journal template selector: https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/tools-for-ieee-authors/ieee-article-templates/
- Conference PDF checking and publication information: https://events.ieee.org/planning-basics/ieee-conference-publications/publishing-information-for-ieee-conference-authors/
- Submission and AI disclosure policy: https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/

The IEEE policy requires disclosure of AI-generated article content, including code, with the tool identified and affected sections explained. The authors should verify the applicable policy and anonymity instructions for their chosen venue. This revision includes generated research-validation code and drafted manuscript text, so it goes beyond grammar-only assistance.

## Draft disclosure for author review

“Codex assisted development of research-validation and audit scripts and revision of methodology, results, and limitations text. The authors remain responsible for experimental design, source-data provenance, verification of generated contributions, and the final manuscript.”

This is a draft, not an assertion that author verification has already occurred. Identify any other tools used in earlier work and describe their contributions before submission. Apply the exact venue's placement and anonymity requirements.

The manuscript now includes an acknowledgment identifying Codex assistance in validation/audit code and methodology, results, and limitations revisions. Review it against the full history of tool use and the chosen venue's anonymity requirements before submission.

## Remaining decisions and external checks

Choose the specific venue, publication category, template, and page limit. Obtain supervisor/coauthor approval, finalize authorship and affiliations as permitted, review the official-source acquisition and conversion chain and its documented scope, run any required similarity and PDF checks, and prepare a reviewed archival release if appropriate. GitHub access is restored and the research update is published. The historical parquet conversion gap is not a source claim for the new primary study. The current project has not been submitted or accepted.
