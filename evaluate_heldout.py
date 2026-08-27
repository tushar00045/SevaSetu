"""
Evaluate the department and urgency classifiers on heldout_test_set.csv -
the hand-written, non-templated test set required by CLAUDE_CODE_BRIEF.md.

Produces:
    heldout_predictions.csv  - every row with predicted label + confidence
    prints accuracy, macro-F1, confusion matrix, the full list of wrong
    predictions, and the confidence distribution (fraction below 0.6,
    which is the backend's auto-route-vs-human-review threshold).

Rows with an empty expected_department are adversarial / no-signal rows -
they are excluded from department accuracy/F1 (there is no correct label
to score against) but ARE used for the confidence-distribution check,
since the desired behavior on them is low confidence.
"""

import pickle

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
)
from tensorflow.keras.models import load_model

HELDOUT_PATH = "heldout_test_set.csv"
DEPT_MODEL_PATH = "sevasetu_department_bilstm.keras"
DEPT_ENCODER_PATH = "department_label_encoder.pkl"
URGENCY_MODEL_PATH = "sevasetu_urgency_bilstm.keras"
URGENCY_ENCODER_PATH = "urgency_label_encoder.pkl"
CONFIDENCE_THRESHOLD = 0.6


def load_pickle(path):
    with open(path, "rb") as f:
        return pickle.load(f)


def predict_batch(model, label_encoder, texts):
    input_tensor = tf.constant(list(texts), dtype=tf.string)
    probs = model.predict(input_tensor, verbose=0)
    preds_idx = np.argmax(probs, axis=1)
    preds = label_encoder.inverse_transform(preds_idx)
    confidences = probs[np.arange(len(probs)), preds_idx]
    return preds, confidences


def main():
    df = pd.read_csv(HELDOUT_PATH, keep_default_na=False)
    print(f"Loaded {len(df)} held-out rows")

    dept_model = load_model(DEPT_MODEL_PATH)
    dept_encoder = load_pickle(DEPT_ENCODER_PATH)
    urgency_model = load_model(URGENCY_MODEL_PATH)
    urgency_encoder = load_pickle(URGENCY_ENCODER_PATH)

    dept_preds, dept_conf = predict_batch(dept_model, dept_encoder, df["complaint_text"])
    urg_preds, urg_conf = predict_batch(urgency_model, urgency_encoder, df["complaint_text"])

    df["predicted_department"] = dept_preds
    df["department_confidence"] = dept_conf
    df["predicted_urgency"] = urg_preds
    df["urgency_confidence"] = urg_conf

    df.to_csv("heldout_predictions.csv", index=False)
    print("Wrote heldout_predictions.csv")

    scored = df[df["expected_department"] != ""].copy()
    adversarial = df[df["expected_department"] == ""].copy()

    print("\n" + "=" * 60)
    print("DEPARTMENT CLASSIFIER - scored rows:", len(scored), "/ adversarial (unscored):", len(adversarial))
    print("=" * 60)

    acc = accuracy_score(scored["expected_department"], scored["predicted_department"])
    macro_f1 = f1_score(scored["expected_department"], scored["predicted_department"], average="macro")
    print(f"Accuracy : {acc:.4f}")
    print(f"Macro-F1 : {macro_f1:.4f}")

    labels = sorted(set(scored["expected_department"]) | set(scored["predicted_department"]))
    cm = confusion_matrix(scored["expected_department"], scored["predicted_department"], labels=labels)
    print("\nConfusion matrix (rows=actual, cols=predicted), labels:")
    for i, lbl in enumerate(labels):
        print(f"  {i}: {lbl}")
    print(cm)

    wrong = scored[scored["expected_department"] != scored["predicted_department"]]
    print(f"\nWRONG PREDICTIONS ({len(wrong)} / {len(scored)}):")
    for _, row in wrong.iterrows():
        print(f"- TEXT: {row['complaint_text']}")
        print(f"  EXPECTED: {row['expected_department']}  PREDICTED: {row['predicted_department']} "
              f"(confidence {row['department_confidence']:.3f})  category={row['category']}")

    below_thresh = (df["department_confidence"] < CONFIDENCE_THRESHOLD).mean()
    print(f"\nFraction of ALL {len(df)} predictions below {CONFIDENCE_THRESHOLD} confidence "
          f"(these route to human review per backend/src/routing.ts): {below_thresh:.4f}")

    adv_below = (adversarial["department_confidence"] < CONFIDENCE_THRESHOLD).mean() if len(adversarial) else float("nan")
    print(f"Fraction of adversarial/no-signal rows below {CONFIDENCE_THRESHOLD} confidence "
          f"(higher is better here - these SHOULD be low confidence): {adv_below:.4f}")

    print("\n" + "=" * 60)
    print("URGENCY CLASSIFIER")
    print("=" * 60)
    urg_scored = df[df["expected_urgency"] != ""].copy()
    urg_acc = accuracy_score(urg_scored["expected_urgency"], urg_scored["predicted_urgency"])
    urg_macro_f1 = f1_score(urg_scored["expected_urgency"], urg_scored["predicted_urgency"], average="macro")
    print(f"Scored rows: {len(urg_scored)} / {len(df)}")
    print(f"Accuracy : {urg_acc:.4f}")
    print(f"Macro-F1 : {urg_macro_f1:.4f}")

    urg_labels = sorted(set(urg_scored["expected_urgency"]) | set(urg_scored["predicted_urgency"]))
    urg_cm = confusion_matrix(urg_scored["expected_urgency"], urg_scored["predicted_urgency"], labels=urg_labels)
    print("Confusion matrix labels:", urg_labels)
    print(urg_cm)

    urg_wrong = urg_scored[urg_scored["expected_urgency"] != urg_scored["predicted_urgency"]]
    print(f"\nURGENCY WRONG PREDICTIONS ({len(urg_wrong)} / {len(urg_scored)}):")
    for _, row in urg_wrong.iterrows():
        print(f"- TEXT: {row['complaint_text']}")
        print(f"  EXPECTED: {row['expected_urgency']}  PREDICTED: {row['predicted_urgency']} "
              f"(confidence {row['urgency_confidence']:.3f})")

    print("\nDone.")


if __name__ == "__main__":
    main()
