"""Build the labelled NORMAL / PROMPT_INJECTION / JAILBREAK dataset used to
fine-tune the DistilBERT classifier behind predict_ml().

Sources, matching the role each is assigned in the project synopsis's own
dataset table (Section 5.3):
  - deepset/prompt-injections (Hugging Face) -> NORMAL (label 0) and
    PROMPT_INJECTION (label 1) examples. Ref [15].
  - TrustAIRLab/in-the-wild-jailbreak-prompts (Hugging Face), the dataset
    behind Shen et al., "'Do Anything Now'" -> JAILBREAK examples
    (400 sampled, per the synopsis's target). Ref [5].
  - JailbreakBench / JBB-Behaviors (Hugging Face) -> harmful behaviours as
    JAILBREAK, benign behaviours as NORMAL (100 + 100, full set). Ref [4].
  - AdvBench (Zou et al., via the original llm-attacks GitHub release CSV —
    not gated, unlike some HF mirrors) -> harmful/adversarial instructions
    as PROMPT_INJECTION (250 sampled), per the synopsis's own
    "adversarial-suffix and harmful-instruction style injection examples"
    role assignment for this source. Ref [3].
  - XSTest (Hugging Face, Paul/XSTest) -> only the "safe" subset (250 of 450)
    used as NORMAL, specifically to reduce over-refusal / false positives on
    benign-but-tricky prompts (the exact rationale XSTest was built for,
    Section 3.1). The "unsafe" subset is harmful-content requests rather
    than injection/jailbreak patterns, so it's deliberately NOT folded into
    PROMPT_INJECTION/JAILBREAK — that would mislabel a different threat
    class as this classifier's target classes. Ref [7].
  - A small hand-written set of everyday benign task prompts (including some
    that mention PII in an ordinary context), added to NORMAL so the model
    also sees short, simple, non-forum-style text.
  - HarmBench is intentionally NOT included — the synopsis itself reserves
    it for adversarial/red-team evaluation from the Minor Project stage
    onward (Section 5.3), not Micro-stage classifier training.

Output: data/train.csv, data/val.csv, data/test.csv (70/15/15 stratified split),
each with columns [text, label] where label in {NORMAL, PROMPT_INJECTION, JAILBREAK}.

These CSVs are intentionally NOT committed to git: the jailbreak/harmful
source corpora contain raw, real-world adversarial/NSFW text, which is
appropriate to use as local training data for a security classifier but not
appropriate to publish verbatim inside the repository. Anyone can regenerate
the exact same split by re-running this script (a fixed random seed is used
throughout).
"""

import os
import random
import re

import pandas as pd
import requests
from datasets import load_dataset
from sklearn.model_selection import train_test_split

SEED = 42
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

LABEL_NORMAL = "NORMAL"
LABEL_INJECTION = "PROMPT_INJECTION"
LABEL_JAILBREAK = "JAILBREAK"

# Sample sizes chosen to track the synopsis's own "Approx. Size Used" column
# (Section 5.3) as closely as each source's actual availability allows.
JAILBREAK_SAMPLE_SIZE = 400
ADVBENCH_SAMPLE_SIZE = 250
ADVBENCH_URL = (
    "https://raw.githubusercontent.com/llm-attacks/llm-attacks/main/"
    "data/advbench/harmful_behaviors.csv"
)

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


def _load_jailbreakbench_source():
    ds = load_dataset("JailbreakBench/JBB-Behaviors", "behaviors")
    rows = []
    for example in ds["harmful"]:
        text = _clean_text(example["Goal"])
        if text:
            rows.append({"text": text, "label": LABEL_JAILBREAK})
    for example in ds["benign"]:
        text = _clean_text(example["Goal"])
        if text:
            rows.append({"text": text, "label": LABEL_NORMAL})
    return rows


def _load_advbench_source():
    response = requests.get(ADVBENCH_URL, timeout=30)
    response.raise_for_status()
    lines = response.text.splitlines()
    reader = pd.read_csv(pd.io.common.StringIO("\n".join(lines)))
    goals = [_clean_text(g) for g in reader["goal"].tolist() if isinstance(g, str) and g.strip()]

    rng = random.Random(SEED)
    if len(goals) > ADVBENCH_SAMPLE_SIZE:
        goals = rng.sample(goals, ADVBENCH_SAMPLE_SIZE)
    return [{"text": g, "label": LABEL_INJECTION} for g in goals]


def _load_xstest_safe_source():
    ds = load_dataset("Paul/XSTest")["train"]
    rows = []
    for example in ds:
        if example["label"] != "safe":
            continue
        text = _clean_text(example["prompt"])
        if text:
            rows.append({"text": text, "label": LABEL_NORMAL})
    return rows


def _load_extra_benign():
    return [{"text": _clean_text(p), "label": LABEL_NORMAL} for p in _EXTRA_BENIGN_PROMPTS]


def build_dataset() -> pd.DataFrame:
    rows = (
        _load_injection_source()
        + _load_jailbreak_source()
        + _load_jailbreakbench_source()
        + _load_advbench_source()
        + _load_xstest_safe_source()
        + _load_extra_benign()
    )
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
