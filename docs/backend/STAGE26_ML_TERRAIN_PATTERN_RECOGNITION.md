# Stage 26 — Machine Learning-Based Terrain Pattern Recognition

## Scope
Adds an optional, supervised Random Forest workflow for numeric terrain-feature samples. Training requires operator-supplied labelled data with provenance. No pretrained model, real planetary training data, synthetic production data, or performance claims are included.

## Setup
Install the optional ML dependencies in an isolated Python environment:

```bash
pip install -r requirements-ml.txt
python -m unittest scripts.test_terrascan_ml -v
```

## Training
Prepare a JSON dataset following `data/ml-training/README.md`, then run:

```bash
python scripts/terrascan_ml.py train path/to/reviewed-labelled-samples.json --output-dir data/ml-models/run-001 --test-fraction 0.25 --seed 42 --trees 300
```

The output directory must not already exist. Training performs a stratified holdout split and writes `model.joblib` plus `evaluation.json`, including class-wise precision/recall/F1, confusion matrix, accuracy, input dataset hash, model hash and split parameters.

## Inference

```bash
python scripts/terrascan_ml.py predict data/ml-models/run-001/model.joblib path/to/unlabelled-samples.json --output data/ml-predictions/run-001.json
```

Inference feature names and order must exactly match the trained model. Results are exploratory and pending human review.

## Scientific and governance safeguards
- At least two classes and two samples per class are required; empty or incomplete data fails closed.
- Every training sample requires explicit label basis and source identifier/SHA-256. This validates metadata shape only; it does not verify that a label is scientifically correct.
- Metrics describe only the supplied holdout split. Small, spatially correlated or imbalanced datasets can make metrics misleading.
- Random Forest class probability outputs are not calibrated probabilities by default.
- A model trained on Earth terrain does not automatically generalize to lunar or Martian sensors, resolutions, illumination, gravity, geology or processing pipelines. Cross-domain validation is a separate requirement.
- No automatic evidence approval, analog ranking, mission suitability, safety determination or operational authorization is performed.
- Do not mix spatially adjacent pixels between train and test and interpret the result as independent generalization. Prefer spatially separated and, where appropriate, cross-body/cross-sensor validation.
- Synthetic fixtures exist only in software tests and are not training evidence.

## Output status
Training evaluation: `trained-evaluated`; predictions: `exploratory-pending-human-review`; evidence approval remains unchanged; mission authorization remains `not-assessed`.
