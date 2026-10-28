# Prompt Guard — DistilBERT Classifier Evaluation Report

Test set size: 389 examples

## Overall metrics

- Accuracy: 0.9434
- Precision (macro): 0.9203
- Recall (macro): 0.9173
- F1-score (macro): 0.9186

## Per-class metrics

| Class | Precision | Recall | F1-score | Support |
| --- | --- | --- | --- | --- |
| NORMAL | 0.9750 | 0.9791 | 0.9770 | 239 |
| PROMPT_INJECTION | 0.8846 | 0.9079 | 0.8961 | 76 |
| JAILBREAK | 0.9014 | 0.8649 | 0.8828 | 74 |

## Confusion matrix

Rows = true label, columns = predicted label.

| | NORMAL | PROMPT_INJECTION | JAILBREAK |
| --- | --- | --- | --- |
| NORMAL | 234 | 3 | 2 |
| PROMPT_INJECTION | 2 | 69 | 5 |
| JAILBREAK | 4 | 6 | 64 |

See `confusion_matrix.png` for a plotted version of this table.

## sklearn classification_report (raw)

```
                  precision    recall  f1-score   support

          NORMAL       0.97      0.98      0.98       239
PROMPT_INJECTION       0.88      0.91      0.90        76
       JAILBREAK       0.90      0.86      0.88        74

        accuracy                           0.94       389
       macro avg       0.92      0.92      0.92       389
    weighted avg       0.94      0.94      0.94       389

```