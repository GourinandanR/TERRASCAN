# Stage 27 — Predictive Terrain Analysis

## Purpose
Adds an optional supervised Random Forest regression workflow to predict one explicitly defined continuous terrain target from operator-supplied numeric features. It is separate from Stage 25 analog retrieval and Stage 26 classification.

## Install and test
```bash
pip install -r requirements-ml.txt
python -m unittest scripts.test_terrascan_predict -v
```

## Train
Prepare a dataset using `data/predictive-training/README.md`, then:
```bash
python scripts/terrascan_predict.py train path/to/reviewed-target-samples.json --output-dir data/predictive-models/run-001 --seed 42 --trees 400 --coverage 0.90
```
The output directory must not exist. Training uses two-stage `GroupShuffleSplit`: independent spatial groups are held apart for training, interval calibration and final testing. It writes `regressor.joblib` and `evaluation.json` with MAE, RMSE, R², residual summary, group counts, dataset/model SHA-256 and empirical interval coverage.

## Predict
```bash
python scripts/terrascan_predict.py predict data/predictive-models/run-001/regressor.joblib path/to/unlabelled-features.json --output data/predictive-results/run-001.json
```
Input feature names and order must exactly match the trained model. Output includes a predicted value and a symmetric residual-calibrated interval.

## Uncertainty and scientific limits
- The interval uses a finite-sample higher empirical quantile of absolute calibration residuals. Its nominal coverage is not a guarantee; small calibration sets are coarse and distribution shift can invalidate coverage.
- Test metrics and interval coverage describe only the supplied dataset and split. They do not establish future predictive validity.
- Spatial grouping reduces one form of leakage only when group IDs genuinely represent independent regions. It does not prove independence.
- Cross-body, cross-sensor, cross-resolution, illumination and processing-chain validation are required before claiming planetary transfer.
- No physical process model, causal model, climate forecast, hazard forecast or mission outcome is simulated.
- Predictions remain `exploratory-pending-human-review`; no evidence approval, site ranking, mission suitability or operational authorization is performed.
- No training dataset or trained model is bundled; synthetic fixtures are test-only.
