# CICIoT2023 Model Reimplementation Progress Report

# 1. Project Goal

The goal of this project is to reimplement and extend machine learning models using the **CICIoT2023** dataset. The paper introduces a large-scale IoT intrusion dataset containing **33 attacks** grouped into **7 categories**, plus benign traffic, and evaluates ML models for **binary**, **grouped multiclass**, and **fine-grained multiclass** classification. The paper reports that **Random Forest** and **Deep Neural Network** were among the strongest baselines in their evaluation.

My implementation goal is slightly different from strict paper reproduction. I am using the paper as a baseline, but my primary practical objective is to build a strong **XGBoost** classifier first, followed by **Random Forest** and possibly a **DNN**.

---

# 2. Dataset Setup

## Training Data
The training data is stored under:

`data/TrainingData`

This directory contains subfolders corresponding to attack types and one benign folder:

- `Benign_Final`
- `Backdoor_Malware`
- `BrowserHijacking`
- `CommandInjection`
- `DDoS-*`
- `DoS-*`
- `DNS_Spoofing`
- `DictionaryBruteForce`
- `MITM-ArpSpoofing`
- `Mirai-*`
- `Recon-*`
- `SqlInjection`
- `Uploading_Attack`
- `VulnerabilityScan`
- `XSS`

The training CSV files do **not** contain a `Label` column, so the class label must be inferred from the **parent folder name**.

## Test Data
The holdout test data is stored under:

`data/CIC_IOT_Dataset_2023`

This directory contains **63 merged CSV files** (`Merged01.csv`, `Merged02.csv`, ...), each with the same 39 features plus a `Label` column.

---

# 3. Reference From the Paper

The paper describes a processed CSV representation of the CICIoT2023 dataset in which network traffic is summarized into extracted features. In the ML evaluation pipeline, the authors combine benign and malicious data and evaluate three tasks:

1. **Binary classification**: benign vs malicious  
2. **8-class grouped classification**: benign + 7 attack groups  
3. **34-class classification**: benign + individual attack classes  

The paper also states that the dataset is normalized with `StandardScaler` before training in their evaluation pipeline, and that Random Forest and DNN remain strong performers in the harder multiclass tasks.

For my implementation, I decided to use the paper as a conceptual baseline but to organize training more practically:

- use `TrainingData/` for train/validation
- reserve the **63 merged CSVs** as a final holdout test set
- prioritize **XGBoost** first
- then compare against **Random Forest**
- then try **DNN** if needed

---

# 4. Notebook 00: Data Audit and Loader

The first notebook was designed to audit the dataset before any model training. Its purpose was to:

- recursively discover all training CSV files
- discover all merged holdout test CSV files
- verify that schemas match expectations
- normalize label names between training and test data
- build label mappings for:
  - 34-class
  - 8-class
  - binary
- save reusable artifact files for downstream notebooks

This notebook is important because it separates **data validation** from **model training**. That makes the project easier to debug and easier to explain.

---

# 5. Feature Schema

The dataset being used contains **39 numeric features**:

- `Header_Length`
- `Protocol Type`
- `Time_To_Live`
- `Rate`
- `fin_flag_number`
- `syn_flag_number`
- `rst_flag_number`
- `psh_flag_number`
- `ack_flag_number`
- `ece_flag_number`
- `cwr_flag_number`
- `ack_count`
- `syn_count`
- `fin_count`
- `rst_count`
- `HTTP`
- `HTTPS`
- `DNS`
- `Telnet`
- `SMTP`
- `SSH`
- `IRC`
- `TCP`
- `UDP`
- `DHCP`
- `ARP`
- `ICMP`
- `IGMP`
- `IPv`
- `LLC`
- `Tot sum`
- `Min`
- `Max`
- `AVG`
- `Std`
- `Tot size`
- `IAT`
- `Number`
- `Variance`

The holdout test files contain the same 39 features plus a `Label` column.

---

# 6. Audit Results

## File Discovery
The data audit notebook successfully identified:

- **309 training CSV files**
- **63 merged test CSV files**

### Insert artifact
**[Insert Artifact A: Screenshot of notebook output showing training/test file counts]**

---

## Schema Verification
All training and test files matched the expected schema:

- **Training schema matches:** 309 / 309
- **Test schema matches:** 63 / 63

This confirms that the feature columns are consistent across both training and test sets.

### Insert artifact
**[Insert Artifact B: Screenshot of schema verification output]**

---

## Label Normalization
Because the training data does not include an explicit `Label` column, labels were inferred from folder names and normalized into a canonical format.

Examples:

- `Benign_Final` → `BENIGN`
- `DDoS-PSHACK_FLOOD` → `DDOS_PSHACK_FLOOD`
- `Mirai-greip_flood` → `MIRAI_GREIP_FLOOD`
- `MITM-ArpSpoofing` → `MITM_ARPSPOOFING`

This made the training and test label spaces compatible.

---

## Label Mapping Tasks
Three label views were created:

### 34-class
Benign + all individual attack classes

### 8-class
Benign + grouped attack families:
- BENIGN
- DDOS
- DOS
- MIRAI
- RECON
- SPOOFING
- WEB
- BRUTEFORCE

### Binary
- BENIGN
- MALICIOUS

---

# 7. Label-Space Validation Results

The label-space check produced the following result:

- **Shared 34-class labels:** 34
- **Train-only labels:** 0
- **Test-only labels:** 1 (`NaN`)

This was not a true class mismatch. It indicates that some rows in the merged test files had missing labels.

After updating the normalization logic, the issue was narrowed down to:

- **Missing test labels:** 9
- **Unknown grouped labels:** 0

This means all real classes match correctly, and only 9 holdout rows have missing labels.

### Interpretation
This is a minor data-quality issue, not a modeling issue. The correct handling is to **exclude unlabeled rows from final test evaluation** and report how many were dropped.

### Insert artifact
**[Insert Artifact C: Screenshot of label-space comparison output]**

---

# 8. Training Data Imbalance Observations

The audit also showed meaningful class imbalance. Based on file counts and aggregate file sizes:

- DDoS classes dominate the training files
- Mirai classes are also heavily represented
- Web attacks and brute-force categories are much smaller
- Benign data comes from only 4 files, although those files are fairly large

This means model evaluation should not rely on accuracy alone. Metrics such as:

- weighted F1
- macro F1
- per-class precision/recall

will be important.

### Insert artifact
**[Insert Artifact D: Table or screenshot of training label distribution]**

---

# 9. Artifacts Produced So Far

The audit notebook produced the following reusable files:

- `artifacts/train_manifest.csv`
- `artifacts/test_manifest.csv`
- `artifacts/test_labels_full.csv`

These are important because they make the next notebooks reproducible and independent from hidden notebook state.

### Suggested artifact inserts
- **Artifact E:** `train_manifest.csv` preview
- **Artifact F:** `test_manifest.csv` preview
- **Artifact G:** `test_labels_full.csv` preview

---

# 10. Debug Sample Loader

A debug sample loader was created to quickly test downstream code without loading the full dataset into memory. A sample run loaded:

- **309,000 rows**
- **43 columns**  
  (39 features + 3 label columns + source file)

This verified that:

- numeric conversion works
- label assignment works
- source-file tracking works

### Insert artifact
**[Insert Artifact H: Screenshot of debug dataframe preview]**

---

# 11. Chunked Loading Strategy

Because the dataset is large, the project was designed around **chunk-based reading** rather than fully concatenating everything into memory.

Chunk iterators were created for:

- training data
- merged holdout test data

This is important because it will allow:

- scalable preprocessing
- class-balanced sampling
- test evaluation without loading all 63 merged CSVs at once

This design choice is especially useful for local hardware constraints, even though the current machine is reasonably capable.

---

# 12. Planned Modeling Strategy

## Primary model
**XGBoost**

Reason:
- strong performance on structured/tabular data
- good practical baseline
- likely to outperform simpler baselines on this feature set

## Secondary baseline
**Random Forest**

Reason:
- directly related to the paper’s strongest classical model
- easy to compare against XGBoost

## Optional third model
**Deep Neural Network**

Reason:
- paper baseline
- useful for comparison
- may improve certain nonlinear decision boundaries, but requires more setup

---

# 13. Planned Evaluation Strategy

The next notebook will train **XGBoost** first on the **34-class** problem.

Evaluation will proceed in this order:

1. **34-class validation**
2. **34-class holdout test**
3. **8-class grouped classification**
4. **binary benign vs malicious**

This structure preserves comparability with the paper while still supporting practical experimentation.

---

# 14. Current Status

At this stage, the dataset preparation phase is complete enough to begin model training.

## Ready:
- file discovery
- schema verification
- label normalization
- label-space matching
- manifest creation
- debug sample loading
- chunk iterators

## Remaining before full experimentation:
- run Notebook 01 for XGBoost
- compute validation metrics
- evaluate on 63-file holdout test set
- compare later against Random Forest and DNN

---

# 15. Main Conclusion So Far

The dataset pipeline is working correctly. There are **no major structural issues** with the data. The only identified issue is **9 missing labels in the holdout test set**, which can be handled cleanly by dropping those rows during evaluation.

This means the project is now ready to move from **data auditing** into **model training**, beginning with XGBoost.

---

# 16. Appendix: Suggested Figures / Artifacts to Add

1. **Artifact A** — file discovery output  
2. **Artifact B** — schema verification output  
3. **Artifact C** — train/test label-space comparison  
4. **Artifact D** — class distribution table  
5. **Artifact E** — preview of `train_manifest.csv`  
6. **Artifact F** — preview of `test_manifest.csv`  
7. **Artifact G** — preview of `test_labels_full.csv`  
8. **Artifact H** — debug sample dataframe preview  
9. **Artifact I** — notebook 00 folder structure screenshot  
10. **Artifact J** — upcoming XGBoost validation metrics table

---
