"""Build the labelled NORMAL / PROMPT_INJECTION / JAILBREAK dataset used to
fine-tune the DistilBERT classifier behind predict_ml().

Sources:
  - deepset/prompt-injections (Hugging Face) -> NORMAL (label 0) and
    PROMPT_INJECTION (label 1) examples. Cited in the project synopsis, Ref [15].
  - TrustAIRLab/in-the-wild-jailbreak-prompts (Hugging Face), the dataset behind
    Shen et al., "'Do Anything Now'" -> JAILBREAK examples. Cited in the
    literature review, Ref [5].
  - A small hand-written set of everyday benign task prompts, added to
    NORMAL so the model also sees short, simple, non-forum-style text.

Output: data/train.csv, data/val.csv, data/test.csv (70/15/15 stratified split),
each with columns [text, label] where label in {NORMAL, PROMPT_INJECTION, JAILBREAK}.

These CSVs are intentionally NOT committed to git: the jailbreak source corpus
contains raw, real-world adversarial/NSFW text scraped from public forums,
which is appropriate to use as local training data for a security classifier
but not appropriate to publish verbatim inside the repository. Anyone can
regenerate the exact same split by re-running this script (a fixed random
seed is used throughout).
"""

import os
import random
import re

import pandas as pd
from datasets import load_dataset
from sklearn.model_selection import train_test_split

SEED = 42
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

LABEL_NORMAL = "NORMAL"
LABEL_INJECTION = "PROMPT_INJECTION"
LABEL_JAILBREAK = "JAILBREAK"

# Number of jailbreak examples to sample from the ~1400-example in-the-wild
# corpus, to keep rough class balance with the injection class (~200-350).
JAILBREAK_SAMPLE_SIZE = 350

_EXTRA_BENIGN_PROMPTS = [
    "Explain what photosynthesis is.",
    "Summarize the plot of Romeo and Juliet in three sentences.",
    "Write a Python function that reverses a string.",
    "What's the difference between TCP and UDP?",
    "Help me plan a healthy meal for dinner tonight.",
    "Translate 'good morning' into French.",
    "Give me three tips for improving my resume.",
    "Explain the difference between machine learning and deep learning.",
    "What is the capital of Australia?",
    "Write a short poem about autumn.",
    "How do I center a div in CSS?",
    "Explain Newton's second law of motion.",
    "Recommend a beginner-friendly book on economics.",
    "What are the main causes of climate change?",
    "Draft a polite email asking my manager for a day off.",
    "How does photosynthesis differ between C3 and C4 plants?",
    "What's a good workout routine for beginners?",
    "Explain how binary search works.",
    "Suggest a name for a new coffee shop.",
    "What is the boiling point of water at sea level?",
    "Describe the water cycle in simple terms.",
    "How do I convert a list to a set in Python?",
    "What are some good study techniques for exams?",
    "Explain the concept of supply and demand.",
    "Write a haiku about the ocean.",
    "What is object-oriented programming?",
    "Give me a recipe for a simple vegetable soup.",
    "Explain how vaccines work.",
    "What are the benefits of regular exercise?",
    "How do I set up a virtual environment in Python?",
    # Benign requests that happen to include contact/personal info framed as a
    # normal task (not an attack) — added after evaluation surfaced these as a
    # false-positive pattern (PII mention + imperative phrasing was being
    # confused with instruction-override injection).
    "My email is john.doe@example.com, please send the invoice there.",
    "My phone number is 555-123-4567, feel free to text me the update.",
    "Here is my name: Priya Sharma. Please add me to the guest list.",
    "My email address is sam@company.com — could you forward this report to it?",
    "Please update my contact record: name Alex Kim, email alex.kim@mail.com.",
    "Process this order for me: customer email is customer@shop.com.",
    "Can you format this data for me? Name: Maria Lopez, Phone: 555-987-6543.",
    "Please save my details: email lisa@example.org, phone 555-222-3333.",
    "Add this contact to my address book: Tom Baker, tom.baker@mail.com.",
    "Send the confirmation to my email, which is user123@example.com.",
    "Here's my information for the form: full name David Chen, email david@test.com.",
    "Please register me with this email: register@myinbox.com.",
]


def _clean_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _load_injection_source():
    ds = load_dataset("deepset/prompt-injections")
    rows = []
    for split in ("train", "test"):
        for example in ds[split]:
            text = _clean_text(example["text"])
            if not text:
                continue
            label = LABEL_INJECTION if example["label"] == 1 else LABEL_NORMAL
            rows.append({"text": text, "label": label})
    return rows


def _load_jailbreak_source():
    ds = load_dataset("TrustAIRLab/in-the-wild-jailbreak-prompts", "jailbreak_2023_12_25")["train"]
    rng = random.Random(SEED)
    prompts = [_clean_text(p) for p in ds["prompt"] if p and p.strip()]
    # DistilBERT truncates at 512 tokens anyway; cap raw length to keep the
    # dataset file and tokenization step fast.
    prompts = [p[:4000] for p in prompts]
    if len(prompts) > JAILBREAK_SAMPLE_SIZE:
        prompts = rng.sample(prompts, JAILBREAK_SAMPLE_SIZE)
    return [{"text": p, "label": LABEL_JAILBREAK} for p in prompts]


def _load_extra_benign():
    return [{"text": _clean_text(p), "label": LABEL_NORMAL} for p in _EXTRA_BENIGN_PROMPTS]


def build_dataset() -> pd.DataFrame:
    rows = _load_injection_source() + _load_jailbreak_source() + _load_extra_benign()
    df = pd.DataFrame(rows)

    before = len(df)
    df = df.drop_duplicates(subset=["text"]).reset_index(drop=True)
    df = df[df["text"].str.len() >= 3].reset_index(drop=True)
    after = len(df)
    print(f"Cleaned dataset: {before} -> {after} rows after dedup/length filtering")

    print(df["label"].value_counts())
    return df


def split_and_save(df: pd.DataFrame) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    train_df, temp_df = train_test_split(
        df, test_size=0.30, random_state=SEED, stratify=df["label"]
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, random_state=SEED, stratify=temp_df["label"]
    )

    train_df.to_csv(os.path.join(DATA_DIR, "train.csv"), index=False)
    val_df.to_csv(os.path.join(DATA_DIR, "val.csv"), index=False)
    test_df.to_csv(os.path.join(DATA_DIR, "test.csv"), index=False)

    print(f"train: {len(train_df)}  val: {len(val_df)}  test: {len(test_df)}")
    print("Saved to", DATA_DIR)


if __name__ == "__main__":
    dataset = build_dataset()
    split_and_save(dataset)
