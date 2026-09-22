"""Fine-tune a DistilBERT sequence classifier for NORMAL / PROMPT_INJECTION /
JAILBREAK detection, to back predict_ml() in ai_ml/classifier.py.

Usage:
    python ai_ml/training/train_classifier.py

Requires data/train.csv and data/val.csv to already exist
(run build_dataset.py first). Saves the fine-tuned model + tokenizer to
ai_ml/models/distilbert-promptguard/, which classifier.py loads at runtime
if present.

The trained checkpoint (~260MB) is NOT committed to git (see .gitignore) —
GitHub rejects files over 100MB on a normal push, and checkpoints are
reproducible artifacts, not source. Re-run this script to regenerate it.
"""

import json
import os

import numpy as np
import pandas as pd
import torch
from datasets import Dataset
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

BASE_MODEL = "distilbert-base-uncased"
TRAINING_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(TRAINING_DIR, "data")
MODEL_DIR = os.path.join(os.path.dirname(TRAINING_DIR), "models", "distilbert-promptguard")

LABELS = ["NORMAL", "PROMPT_INJECTION", "JAILBREAK"]
LABEL2ID = {label: i for i, label in enumerate(LABELS)}
ID2LABEL = {i: label for i, label in enumerate(LABELS)}

SEED = 42


def _load_split(name: str) -> Dataset:
    df = pd.read_csv(os.path.join(DATA_DIR, f"{name}.csv"))
    df["labels"] = df["label"].map(LABEL2ID)
    return Dataset.from_pandas(df[["text", "labels"]], preserve_index=False)


def _compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    acc = accuracy_score(labels, preds)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="macro", zero_division=0
    )
    return {"accuracy": acc, "precision": precision, "recall": recall, "f1": f1}


def main():
    torch.manual_seed(SEED)

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=256)

    train_ds = _load_split("train").map(tokenize, batched=True)
    val_ds = _load_split("val").map(tokenize, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(LABELS),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    training_args = TrainingArguments(
        output_dir=os.path.join(TRAINING_DIR, "checkpoints"),
        num_train_epochs=4,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        learning_rate=2e-5,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        logging_steps=10,
        seed=SEED,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=data_collator,
        compute_metrics=_compute_metrics,
    )

    trainer.train()

    val_metrics = trainer.evaluate()
    print("Validation metrics:", val_metrics)

    os.makedirs(MODEL_DIR, exist_ok=True)
    trainer.save_model(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)

    with open(os.path.join(MODEL_DIR, "label_map.json"), "w") as f:
        json.dump({"id2label": ID2LABEL, "label2id": LABEL2ID}, f, indent=2)

    with open(os.path.join(TRAINING_DIR, "results", "validation_metrics.json"), "w") as f:
        json.dump(val_metrics, f, indent=2)

    print("Saved model to", MODEL_DIR)


if __name__ == "__main__":
    main()
