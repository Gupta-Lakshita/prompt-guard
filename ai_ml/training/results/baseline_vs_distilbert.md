# Baseline (scikit-learn) vs. DistilBERT — Classifier Comparison

Quantifies the value added by the fine-tuned transformer classifier over classical ML, per synopsis Section 5.4/8. All models trained and evaluated on the exact same train/val/test split.

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) |
| --- | --- | --- | --- | --- |
| TF-IDF + Logistic Regression | 0.9177 | 0.8857 | 0.9001 | 0.8916 |
| TF-IDF + Linear SVM | 0.9409 | 0.9245 | 0.9219 | 0.9231 |
| DistilBERT (fine-tuned transformer) | 0.9434 | 0.9203 | 0.9173 | 0.9186 |

DistilBERT's macro F1 is -0.0045 vs. the best scikit-learn baseline (lower or equal is worth investigating).

## Per-class breakdown

### NORMAL

| Model | Precision | Recall | F1 |
| --- | --- | --- | --- |
| TF-IDF + Logistic Regression | 0.9698 | 0.9414 | 0.9554 |
| TF-IDF + Linear SVM | 0.9625 | 0.9665 | 0.9645 |
| DistilBERT | 0.9750 | 0.9791 | 0.9770 |

### PROMPT_INJECTION

| Model | Precision | Recall | F1 |
| --- | --- | --- | --- |
| TF-IDF + Logistic Regression | 0.8140 | 0.9211 | 0.8642 |
| TF-IDF + Linear SVM | 0.9221 | 0.9342 | 0.9281 |
| DistilBERT | 0.8846 | 0.9079 | 0.8961 |

### JAILBREAK

| Model | Precision | Recall | F1 |
| --- | --- | --- | --- |
| TF-IDF + Logistic Regression | 0.8732 | 0.8378 | 0.8552 |
| TF-IDF + Linear SVM | 0.8889 | 0.8649 | 0.8767 |
| DistilBERT | 0.9014 | 0.8649 | 0.8828 |
