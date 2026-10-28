"""Train and evaluate a scikit-learn baseline classifier (TF-IDF +
Logistic Regression, plus a Linear SVM for comparison) on the SAME
NORMAL/PROMPT_INJECTION/JAILBREAK dataset and train/val/test split used for
the DistilBERT classifier — to quantify "the value added by machine
learning [the transformer] over simple pattern matching" (synopsis
Section 5.4), which otherwise has no baseline to compare against.

This is a classical-ML baseline (bag-of-words style features), distinct
from the regex/heuristic rule engine in ai_ml/rule_engine.py — the synopsis
names both as separate baseline concepts (Section 5.4 "rule-based baseline"
vs Section 8 "scikit-learn (TF-IDF + logistic regression / linear SVM)
baseline"). This script covers the latter, which was previously entirely
missing.

Usage:
    python ai_ml/training/train_baseline.py

Requires data/train.csv and data/test.csv (run build_dataset.py first).

Writes:
    results/baseline_metrics.json
    results/baseline_confusion_matrix.png
    results/baseline_vs_distilbert.md   (only if results/test_metrics.json,
                                          the DistilBERT eval output, exists)
"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

TRAINING_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(TRAINING_DIR, "data")
RESULTS_DIR = os.path.join(TRAINING_DIR, "results")

LABELS = ["NORMAL", "PROMPT_INJECTION", "JAILBREAK"]
SEED = 42


def _load_split(name: str):
    df = pd.read_csv(os.path.join(DATA_DIR, f"{name}.csv"))
    return df["text"].tolist(), df["label"].tolist()


def _build_pipeline(classifier):
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    max_features=20000,
                    sublinear_tf=True,
                ),
            ),
            ("clf", classifier),
        ]
    )


def _evaluate(name, pipeline, X_test, y_test):
    y_pred = pipeline.predict(X_test)

    accuracy = (pd.Series(y_pred) == pd.Series(y_test)).mean()
    precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
        y_test, y_pred, average="macro", zero_division=0, labels=LABELS
    )
    precision_per, recall_per, f1_per, support_per = precision_recall_fscore_support(
        y_test, y_pred, labels=LABELS, zero_division=0
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
        "model": name,
        "accuracy": float(accuracy),
        "precision_macro": float(precision_macro),
        "recall_macro": float(recall_macro),
        "f1_macro": float(f1_macro),
        "per_class": per_class,
        "n_test_examples": len(y_test),
    }

    cm = confusion_matrix(y_test, y_pred, labels=LABELS)

    print(f"\n=== {name} ===")
    print(classification_report(y_test, y_pred, labels=LABELS, zero_division=0))

    return metrics, cm


def _save_confusion_matrix(cm, title, out_path):
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=LABELS)
    fig, ax = plt.subplots(figsize=(6, 5))
    disp.plot(ax=ax, cmap="Oranges", colorbar=True)
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)


def _write_comparison_report(baseline_metrics_by_model):
    distilbert_path = os.path.join(RESULTS_DIR, "test_metrics.json")
    if not os.path.exists(distilbert_path):
        print(
            "No DistilBERT results/test_metrics.json found yet (run "
            "train_classifier.py + evaluate.py first) — skipping the "
            "comparison report; baseline-only metrics are still saved."
        )
        return

    with open(distilbert_path) as f:
        distilbert_metrics = json.load(f)

    lines = [
        "# Baseline (scikit-learn) vs. DistilBERT — Classifier Comparison",
        "",
        "Quantifies the value added by the fine-tuned transformer classifier "
        "over classical ML, per synopsis Section 5.4/8. All models trained and "
        "evaluated on the exact same train/val/test split.",
        "",
        "| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for m in baseline_metrics_by_model:
        lines.append(
            f"| {m['model']} | {m['accuracy']:.4f} | {m['precision_macro']:.4f} "
            f"| {m['recall_macro']:.4f} | {m['f1_macro']:.4f} |"
        )
    lines.append(
        f"| DistilBERT (fine-tuned transformer) | {distilbert_metrics['accuracy']:.4f} "
        f"| {distilbert_metrics['precision_macro']:.4f} "
        f"| {distilbert_metrics['recall_macro']:.4f} "
        f"| {distilbert_metrics['f1_macro']:.4f} |"
    )

    best_baseline_f1 = max(m["f1_macro"] for m in baseline_metrics_by_model)
    delta = distilbert_metrics["f1_macro"] - best_baseline_f1
    lines += [
        "",
        f"DistilBERT's macro F1 is {delta:+.4f} vs. the best scikit-learn baseline "
        f"({'higher' if delta > 0 else 'lower or equal'} is "
        f"{'the expected direction' if delta >= 0 else 'worth investigating'}).",
        "",
        "## Per-class breakdown",
        "",
    ]
    for label in LABELS:
        lines.append(f"### {label}")
        lines.append("")
        lines.append("| Model | Precision | Recall | F1 |")
        lines.append("| --- | --- | --- | --- |")
        for m in baseline_metrics_by_model:
            pc = m["per_class"][label]
            lines.append(f"| {m['model']} | {pc['precision']:.4f} | {pc['recall']:.4f} | {pc['f1']:.4f} |")
        pc = distilbert_metrics["per_class"][label]
        lines.append(
            f"| DistilBERT | {pc['precision']:.4f} | {pc['recall']:.4f} | {pc['f1']:.4f} |"
        )
        lines.append("")

    with open(os.path.join(RESULTS_DIR, "baseline_vs_distilbert.md"), "w") as f:
        f.write("\n".join(lines))
    print("Saved comparison report to results/baseline_vs_distilbert.md")


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    X_train, y_train = _load_split("train")
    X_test, y_test = _load_split("test")

    models = {
        "TF-IDF + Logistic Regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=SEED
        ),
        "TF-IDF + Linear SVM": LinearSVC(class_weight="balanced", random_state=SEED),
    }

    all_metrics = []
    for name, clf in models.items():
        pipeline = _build_pipeline(clf)
        pipeline.fit(X_train, y_train)
        metrics, cm = _evaluate(name, pipeline, X_test, y_test)
        all_metrics.append(metrics)

        safe_name = name.lower().replace(" ", "_").replace("+", "and")
        _save_confusion_matrix(
            cm,
            f"{name} — Confusion Matrix (test set)",
            os.path.join(RESULTS_DIR, f"baseline_confusion_matrix_{safe_name}.png"),
        )

    with open(os.path.join(RESULTS_DIR, "baseline_metrics.json"), "w") as f:
        json.dump(all_metrics, f, indent=2)
    print("\nSaved results/baseline_metrics.json")

    _write_comparison_report(all_metrics)


if __name__ == "__main__":
    main()
