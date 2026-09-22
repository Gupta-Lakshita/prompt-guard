# Prompt Guard — DistilBERT Classifier Evaluation Report

Test set size: 158 examples

## Overall metrics

- Accuracy: 0.9367
- Precision (macro): 0.9442
- Recall (macro): 0.9188
- F1-score (macro): 0.9284

## Per-class metrics

| Class | Precision | Recall | F1-score | Support |
| --- | --- | --- | --- | --- |
| NORMAL | 0.8933 | 1.0000 | 0.9437 | 67 |
| PROMPT_INJECTION | 0.9394 | 0.7949 | 0.8611 | 39 |
| JAILBREAK | 1.0000 | 0.9615 | 0.9804 | 52 |

## Confusion matrix

Rows = true label, columns = predicted label.

| | NORMAL | PROMPT_INJECTION | JAILBREAK |
| --- | --- | --- | --- |
| NORMAL | 67 | 0 | 0 |
| PROMPT_INJECTION | 8 | 31 | 0 |
| JAILBREAK | 0 | 2 | 50 |

See `confusion_matrix.png` for a plotted version of this table.

## sklearn classification_report (raw)

```
                  precision    recall  f1-score   support

          NORMAL       0.89      1.00      0.94        67
PROMPT_INJECTION       0.94      0.79      0.86        39
       JAILBREAK       1.00      0.96      0.98        52

        accuracy                           0.94       158
       macro avg       0.94      0.92      0.93       158
    weighted avg       0.94      0.94      0.94       158

```