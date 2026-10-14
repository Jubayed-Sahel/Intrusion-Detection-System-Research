# Overview of the project

This folder is a visual, beginner-friendly guide to the complete explainable intrusion-detection research project. View the PNG files in number order.

1. **01-project-big-picture.png** - the problem, system, and main conclusion in one page.
2. **02-end-to-end-workflow.png** - the path from raw traffic data to the IEEE paper.
3. **03-data-cleaning-and-leakage-control.png** - why duplicates and train-test overlap were removed.
4. **04-how-the-black-box-is-explained.png** - how TreeSHAP and LIME describe model behavior.
5. **05-how-explanations-are-tested.png** - controls that prevent blind trust in explanations.
6. **06-key-research-results.png** - the main detection and explainability results.
7. **07-alert-evidence-decision.png** - how an alert becomes supported, review-required, or unsupported.
8. **08-how-the-paper-was-built.png** - how experiment evidence becomes an IEEE manuscript.
9. **09-limitations-and-next-steps.png** - what is solved, what is not, and future work.

## Main idea in plain language

Random Forest and XGBoost can detect attacks but are difficult to inspect directly. TreeSHAP and LIME rank features for individual predictions. This project tests those rankings by masking important, unimportant, and random features and measuring whether the model changes as expected. The black box becomes more inspectable, but a model explanation is not proof of real-world causation.

## Regenerate the pictures

From the project root, run:

```powershell
.\.venv\Scripts\python.exe ".\Overview of the project\generate_overview_images.py"
```

The generator reads the saved CSV and JSON experiment outputs, so numerical labels stay connected to reproducible evidence.
