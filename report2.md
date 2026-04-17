# Report 2: 8-Class XGBoost Generalization Diagnosis

## Audience Note
This report is written for an early-stage ML practitioner. I use academic terms, and each term is defined either at first use or in the glossary.

## 1. Executive Summary
The pipeline is functioning end-to-end, but the 8-class XGBoost model has a large generalization gap.

Generalization means how well a model performs on unseen data, not just on data similar to what it was trained on.

Current baseline metrics:
- Validation accuracy: 0.8829518046
- Validation macro F1: 0.8434636376
- Holdout accuracy: 0.6045066885
- Holdout macro F1: 0.4602090484
- Holdout rows evaluated: 45,018,243

This means the model is much stronger on validation than on true holdout, so the core problem is model generalization under distribution mismatch, not data loading or infrastructure.

## 2. Glossary (Academic Terms, Defined)
- Baseline: the first strong reference model used for comparison with future experiments.
- Holdout set: a final test set that is not used for model fitting and is used to estimate real-world performance.
- Validation set: a split of training data used for tuning and model checks before final holdout testing.
- Stratified split: a split that preserves class proportions as much as possible.
- Class imbalance: unequal class frequencies in data.
- Class prior: the proportion of each class in a dataset.
- Distribution shift: train and test data come from different statistical distributions.
- Covariate shift: feature distributions change between train and test.
- Overfitting: a model learns patterns specific to training/validation context that do not transfer to unseen data.
- Data leakage: accidental exposure of target-related information that makes evaluation too optimistic.
- Precision: among predicted positives for a class, the fraction that is correct.
- Recall: among true positives for a class, the fraction recovered by the model.
- F1 score: harmonic mean of precision and recall.
- Macro F1: unweighted average of class-wise F1, giving each class equal importance.
- Weighted F1: class-wise F1 averaged with support weights, so large classes dominate.
- Support: number of true samples for a class.
- Confusion matrix: table of true classes vs predicted classes.
- Feature importance (gain): contribution of a feature to reduction in model loss across tree splits.
- Ablation study: controlled experiment that changes one component while keeping others fixed.

## 3. Baseline Setup (What Was Already Working)
### 3.1 Data and labels
- Target: 8-class label grouping in label_8.
- Features: 39 engineered network traffic features.
- Training sampler: cap-based class balancing up to 50,000 rows per class, with smaller classes below cap.
- Validation split: stratified random row split with 20 percent validation.

### 3.2 Model
- Model: XGBoost multiclass classifier.
- Objective: multi:softprob.
- Eval metric: mlogloss.
- Trees: 600 estimators, depth 8, learning rate 0.05, hist tree method, CUDA device.

## 4. Why New Diagnostic Changes Were Added
The new cells were added to answer one scientific question:

Why is validation much better than holdout?

The added diagnostics were:
1. Gain-based feature importance chart and CSV export.
2. Holdout class support vs holdout F1 scatter.
3. Validation vs holdout per-class comparison table with F1 gap.
4. Weighted-class XGBoost ablation using sample weights, then full holdout evaluation.

## 5. Decision Log (Thought Process Behind Each Change)
This is a structured reasoning log rather than hidden internal chain-of-thought.

### Step A: Check feature reliance concentration
Hypothesis:
The model may rely too heavily on a narrow feature subset, making it brittle under shift.

Action:
Computed gain-based feature importance from the trained XGBoost booster and plotted top 20 features.

Key result:
Top features were highly concentrated, especially Protocol Type, Number, Tot sum, syn_flag_number, UDP, SSH, ack_count, HTTPS.

Interpretation:
The model likely learns strong protocol and traffic-volume signatures. This can work very well for dominant flood-like patterns but may transfer poorly to subtler or mixed-behavior classes.

Decision:
Continue with class-specific diagnostics to see which classes collapse under holdout.

### Step B: Test whether weak classes are only the smallest classes
Hypothesis:
Low F1 might be caused only by tiny holdout class support.

Action:
Sorted holdout per-class metrics by F1 and support, then plotted support vs F1 on log-scale support.

Key result:
- WEB and BRUTEFORCE are small and weak.
- RECON is not tiny (661,108 samples) and still extremely weak.
- DOS is very large (7,746,340) and still mediocre.

Interpretation:
Poor performance is not only a small-class data volume issue. Class separability and transfer mismatch are major factors.

Decision:
Measure class-wise validation-to-holdout drops directly.

### Step C: Quantify per-class validation-to-holdout generalization gap
Hypothesis:
Some classes overfit the sampled/row-split validation setting.

Action:
Saved validation per-class metrics, merged with holdout per-class metrics, and computed per-class F1 gap.

Largest F1 drops (validation minus holdout):
- RECON: +0.7955
- WEB: +0.6154
- DOS: +0.6030
- BRUTEFORCE: +0.3983
- SPOOFING: +0.3812
- DDOS: +0.2720
- MIRAI: +0.0067
- BENIGN: -0.0062

Interpretation:
Validation is optimistic for several classes, especially RECON and WEB. MIRAI transfers well, indicating class-dependent transferability.

Decision:
Run a controlled class weighting ablation to test if imbalance-aware fitting helps.

### Step D: Class weighting ablation with same model configuration
Hypothesis:
Sample weighting may improve minority and weak classes in holdout.

Action:
Trained a cloned model with balanced sample weights and identical hyperparameters. Evaluated on validation and full holdout.

Validation result:
- Weighted validation accuracy: 0.8785569482
- Weighted validation macro F1: 0.8405584943

Holdout result:
- Weighted holdout accuracy: 0.6013699824
- Weighted holdout macro F1: 0.4436334284

Interpretation:
Weighting did not improve holdout macro F1 and slightly degraded overall holdout performance.

Decision:
Reject class weighting as a standalone fix in this setup.

## 6. Current Model Performance (Detailed)
### 6.1 Overall metrics summary
| Model | Validation Accuracy | Validation Macro F1 | Holdout Accuracy | Holdout Macro F1 | Holdout Weighted F1 |
|---|---:|---:|---:|---:|---:|
| Baseline XGBoost | 0.8830 | 0.8435 | 0.6045 | 0.4602 | 0.6734 |
| Weighted XGBoost | 0.8786 | 0.8406 | 0.6014 | 0.4436 | 0.6723 |

Generalization gap (baseline):
- Accuracy gap: about 0.2784
- Macro F1 gap: about 0.3833

### 6.2 Baseline holdout per-class performance
| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| MIRAI | 0.9954 | 0.9907 | 0.9930 | 2,521,551 |
| BENIGN | 0.8037 | 0.7829 | 0.7931 | 1,051,313 |
| DDOS | 0.8737 | 0.6229 | 0.7273 | 32,535,697 |
| SPOOFING | 0.6801 | 0.3370 | 0.4507 | 465,914 |
| DOS | 0.3800 | 0.4139 | 0.3962 | 7,746,340 |
| BRUTEFORCE | 0.1304 | 0.5989 | 0.2142 | 12,522 |
| WEB | 0.0301 | 0.7295 | 0.0578 | 23,798 |
| RECON | 0.0265 | 0.3598 | 0.0493 | 661,108 |

Observation:
Some classes have high recall but very low precision (especially WEB and RECON), indicating many false positives.

### 6.3 Weighted ablation holdout class deltas (weighted minus baseline F1)
| Class | F1 Delta |
|---|---:|
| MIRAI | +0.0005 |
| DOS | -0.0003 |
| DDOS | -0.0008 |
| WEB | -0.0023 |
| BENIGN | -0.0028 |
| RECON | -0.0066 |
| SPOOFING | -0.0316 |
| BRUTEFORCE | -0.0887 |

Observation:
The weighting strategy hurt more classes than it helped on holdout.

## 7. Main Issues Noticed
### 7.1 Statistical and modeling issues
1. Distribution mismatch between sampled training/validation and real holdout.
- Training pool is roughly balanced by cap.
- Holdout is extremely imbalanced.
- This changes class priors and can distort learned decision boundaries.

2. Validation protocol optimism.
- Validation uses random row-level split inside sampled pool.
- Final evaluation is file-based merged holdout with different distribution characteristics.
- Result: optimistic validation estimates for several classes.

3. Class heterogeneity in grouped labels.
- Grouped classes like WEB and RECON likely combine behaviorally diverse attack types.
- One grouped classifier can struggle when intra-class variance is high.

4. Precision-recall asymmetry on weak classes.
- RECON and WEB recall is high while precision is extremely low.
- The model is over-triggering these classes, producing many false positives.

### 7.2 Notebook/code quality issues noticed (not blockers, but worth cleanup)
1. Duplicate imports in the imports cell (for example subprocess and xgboost appear multiple times).
2. Minor typos in markdown headings (for example chunck).
3. Environment diagnostic code is extensive in config cell and could be separated from modeling cells for readability.

## 8. What This Means Scientifically
The failure mode is most consistent with distribution-shifted generalization error, not pipeline breakage and not obvious data leakage.

If there were severe leakage, we would expect unrealistically perfect behavior broadly and often small train/validation-to-test inconsistency patterns. Here, the behavior is class-specific and aligned with shift and class-prior mismatch.

## 9. Recommended Next Experiments (In Priority Order)
1. Use file-aware validation (group-based split) instead of row-random validation.
- Group-based split means all rows from the same source file stay in one split.
- This gives a more realistic estimate of holdout performance.

2. Build a binary baseline (BENIGN vs MALICIOUS).
- This checks whether coarse attack detection generalizes better than fine-grained multiclass mapping.

3. Add a Random Forest baseline on the same sampled data.
- A model family comparison helps verify whether the issue is model-specific or data-split-specific.

4. Revisit label grouping strategy for weak classes.
- Consider whether WEB and RECON should be subdivided or represented with additional class-specific features.

5. Keep weighting optional, not default.
- Current balanced sample weighting did not improve holdout macro F1.

## 10. Artifacts Produced During This Diagnosis
- notebooks/artifacts/models/xgb_8class_feature_importance_gain.csv
- notebooks/artifacts/models/xgb_8class_validation_per_class.csv
- notebooks/artifacts/models/xgb_8class_weighted_validation_per_class.csv
- notebooks/artifacts/models/xgb_8class_weighted.joblib
- notebooks/artifacts/models/xgb_8class_weighted_test_per_class.csv
- notebooks/artifacts/models/xgb_8class_weighted_test_confusion_matrix.csv
- notebooks/artifacts/models/xgb_8class_weighted_test_metrics.json

## 11. Brief Message for Dr. Li
The data pipeline and preprocessing are complete, and the end-to-end 8-class XGBoost baseline is running correctly. The current bottleneck is generalization: validation performance is much higher than holdout performance. We completed targeted diagnostics on feature reliance, class support versus F1, class-wise validation-to-holdout gaps, and a weighted-class ablation. The evidence indicates a distribution-mismatch and split-optimism problem rather than infrastructure failure. The next phase is to improve evaluation realism and compare targeted baselines before architectural expansion.
