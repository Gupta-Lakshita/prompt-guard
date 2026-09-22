"""Evaluate the fine-tuned DistilBERT classifier on the held-out test split.

Usage:
    python ai_ml/training/evaluate.py

Requires a model already trained at ai_ml/models/distilbert-promptguard
(run train_classifier.py first) and data/test.csv (run build_dataset.py first).

Writes:
    results/test_metrics.json        - accuracy/precision/recall/F1 (macro + per-class)
    results/confusion_matrix.png     - confusion matrix heatmap
    results/confusion_matrix.csv     - raw confusion matrix counts
    results/evaluation_report.md     - human-readable summary for the report/PPT
"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from transformers import AutoModelForSequenceClassification, AutoTokenizer

TRAINING_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(TRAINING_DIR, "data")
RESULTS_DIR = os.path.join(TRAINING_DIR, "results")
MODEL_DIR = os.path.join(os.path.dirname(TRAINING_DIR), "models", "distilbert-promptguard")

LABELS = ["NORMAL", "PROMPT_INJECTION", "JAILBREAK"]


def load_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    model.eval()
    return tokenizer, model


@torch.no_grad()
def predict_batch(tokenizer, model, texts, batch_size=32):
    preds = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        inputs = tokenizer(batch, truncation=True, max_length=256, padding=True, return_tensors="pt")
        logits = model(**inputs).logits
        preds.extend(torch.argmax(logits, dim=-1).tolist())
    return preds


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    test_df = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))
    label2id = {label: i for i, label in enumerate(LABELS)}
    y_true = test_df["label"].map(label2id).tolist()

    tokenizer, model = load_model()
    y_pred = predict_batch(tokenizer, model, test_df["text"].tolist())

    accuracy = float(np.mean(np.array(y_true) == np.array(y_pred)))
    precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    precision_per, recall_per, f1_per, support_per = precision_recall_fscore_support(
        y_true, y_pred, labels=list(range(len(LABELS))), zero_division=0
    )

    per_class = {
        LABELS[i]: {
            "precision": float(precision_per[i]),
            "recall": float(recall_per[i]),
            "f1": float(f1_per[i]),
            "support": int(support_per[i]),
        }
        for i in range(len(LABELS))
    }

    metrics = {
        "accuracy": accuracy,
        "precision_macro": float(precision_macro),
        "recall_macro": float(recall_macro),
        "f1_macro": float(f1_macro),
        "per_class": per_class,
        "n_test_examples": len(test_df),
    }

    with open(os.path.join(RESULTS_DIR, "test_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(LABELS))))
    pd.DataFrame(cm, index=LABELS, columns=LABELS).to_csv(
        os.path.join(RESULTS_DIR, "confusion_matrix.csv")
    )

    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=LABELS)
    fig, ax = plt.subplots(figsize=(6, 5))
    disp.plot(ax=ax, cmap="Blues", colorbar=True)
    ax.set_title("Prompt Guard DistilBERT Classifier — Confusion Matrix (test set)")
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "confusion_matrix.png"), dpi=150)
    plt.close(fig)

    report_text = classification_report(y_true, y_pred, target_names=LABELS, zero_division=0)

    report_md = [
        "# Prompt Guard — DistilBERT Classifier Evaluation Report",
        "",
        f"Test set size: {len(test_df)} examples",
        "",
        "## Overall metrics",
        "",
        f"- Accuracy: {accuracy:.4f}",
        f"- Precision (macro): {precision_macro:.4f}",
        f"- Recall (macro): {recall_macro:.4f}",
        f"- F1-score (macro): {f1_macro:.4f}",
        "",
        "## Per-class metrics",
        "",
        "| Class | Precision | Recall | F1-score | Support |",
        "| --- | --- | --- | --- | --- |",
    ]
    for label in LABELS:
        m = per_class[label]
        report_md.append(
            f"| {label} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['support']} |"
        )
    report_md += [
        "",
        "## Confusion matrix",
        "",
        "Rows = true label, columns = predicted label.",
        "",
        "| | " + " | ".join(LABELS) + " |",
        "| --- | " + " | ".join(["---"] * len(LABELS)) + " |",
    ]
    for i, label in enumerate(LABELS):
        report_md.append(f"| {label} | " + " | ".join(str(x) for x in cm[i]) + " |")

    report_md += [
        "",
        "See `confusion_matrix.png` for a plotted version of this table.",
        "",
        "## sklearn classification_report (raw)",
        "",
        "```",
        report_text,
        "```",
    ]

    with open(os.path.join(RESULTS_DIR, "evaluation_report.md"), "w") as f:
        f.write("\n".join(report_md))

    print(report_text)
    print("Saved metrics/report/confusion matrix to", RESULTS_DIR)


if __name__ == "__main__":
    main()
