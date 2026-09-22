# Prompt Guard — DistilBERT Classifier Evaluation Report

Test set size: 269 examples

## Overall metrics

- Accuracy: 0.8736
- Precision (macro): 0.8765
- Recall (macro): 0.8598
- F1-score (macro): 0.8643

## Per-class metrics

| Class | Precision | Recall | F1-score | Support |
| --- | --- | --- | --- | --- |
| NORMAL | 0.8889 | 0.9412 | 0.9143 | 119 |
| PROMPT_INJECTION | 0.8072 | 0.8816 | 0.8428 | 76 |
| JAILBREAK | 0.9333 | 0.7568 | 0.8358 | 74 |

## Confusion matrix

Rows = true label, columns = predicted label.

| | NORMAL | PROMPT_INJECTION | JAILBREAK |
| --- | --- | --- | --- |
| NORMAL | 112 | 6 | 1 |
| PROMPT_INJECTION | 6 | 67 | 3 |
| JAILBREAK | 8 | 10 | 56 |

See `confusion_matrix.png` for a plotted version of this table.

## sklearn classification_report (raw)

```
                  precision    recall  f1-score   support

          NORMAL       0.89      0.94      0.91       119
PROMPT_INJECTION       0.81      0.88      0.84        76
       JAILBREAK       0.93      0.76      0.84        74

        accuracy                           0.87       269
       macro avg       0.88      0.86      0.86       269
    weighted avg       0.88      0.87      0.87       269

```