"""
SevaSetu - Urgency Classifier (v2)
Model: Embedding + Bidirectional LSTM
Dataset: sevasetu_grievance_dataset_v2.csv (see generate_dataset.py)

Unlike v1, urgency labels in this dataset are derived from textual danger
/ injury / emergency cues in each sentence (see derive_urgency() in
generate_dataset.py), not from a sector lookup table - any department can
produce a low, medium, or high urgency complaint. Same Embedding + BiLSTM
architecture as the original notebook.
"""

import pickle
import re

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras import Sequential
from tensorflow.keras.callbacks import (
    EarlyStopping,
    ModelCheckpoint,
    ReduceLROnPlateau,
)
from tensorflow.keras.layers import (
    BatchNormalization,
    Bidirectional,
    Dense,
    Dropout,
    Embedding,
    LSTM,
    TextVectorization,
)

DATASET_PATH = "sevasetu_grievance_dataset_v2.csv"
MODEL_PATH = "sevasetu_urgency_bilstm.keras"
LABEL_ENCODER_PATH = "urgency_label_encoder.pkl"
VOCAB_PATH = "urgency_vocabulary.pkl"

MAX_VOCAB_SIZE = 30000
MAX_SEQUENCE_LENGTH = 150
EMBEDDING_DIM = 128
LSTM_UNITS = 128
BATCH_SIZE = 128
EPOCHS = 15
RANDOM_STATE = 42

tf.random.set_seed(RANDOM_STATE)
np.random.seed(RANDOM_STATE)


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def main():
    print("\nLoading dataset...")
    df = pd.read_csv(DATASET_PATH)
    print("Dataset shape:", df.shape)

    data = df[["complaint_text", "urgency"]].copy()
    data.dropna(subset=["complaint_text", "urgency"], inplace=True)
    data["complaint_text"] = data["complaint_text"].astype(str).apply(clean_text)
    data["urgency"] = data["urgency"].astype(str).str.lower().str.strip()

    valid_classes = ["low", "medium", "high"]
    data = data[data["urgency"].isin(valid_classes)].copy()

    before = len(data)
    data.drop_duplicates(subset=["complaint_text", "urgency"], inplace=True)
    print("Duplicates removed:", before - len(data))
    print("Remaining rows:", len(data))

    print("\nUrgency distribution:")
    print(data["urgency"].value_counts())
    print((data["urgency"].value_counts(normalize=True) * 100).round(2))

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(data["urgency"])
    for i, label in enumerate(label_encoder.classes_):
        print(i, "->", label)

    X = data["complaint_text"].values

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=RANDOM_STATE, stratify=y_temp
    )
    print("\nTraining:", len(X_train), "Validation:", len(X_val), "Testing:", len(X_test))

    class_weights = compute_class_weight(
        class_weight="balanced", classes=np.unique(y_train), y=y_train
    )
    class_weight_dict = dict(enumerate(class_weights))
    print("\nClass weights (to counter urgency class imbalance):", class_weight_dict)

    vectorizer = TextVectorization(
        max_tokens=MAX_VOCAB_SIZE,
        output_mode="int",
        output_sequence_length=MAX_SEQUENCE_LENGTH,
        standardize="lower_and_strip_punctuation",
    )
    vectorizer.adapt(X_train)
    vocab_size = len(vectorizer.get_vocabulary())
    print("Vocabulary size (learned from training data only):", vocab_size)

    train_dataset = (
        tf.data.Dataset.from_tensor_slices((X_train, y_train))
        .shuffle(10000)
        .batch(BATCH_SIZE)
        .prefetch(tf.data.AUTOTUNE)
    )
    val_dataset = (
        tf.data.Dataset.from_tensor_slices((X_val, y_val))
        .batch(BATCH_SIZE)
        .prefetch(tf.data.AUTOTUNE)
    )
    test_dataset = (
        tf.data.Dataset.from_tensor_slices((X_test, y_test))
        .batch(BATCH_SIZE)
        .prefetch(tf.data.AUTOTUNE)
    )

    num_classes = len(label_encoder.classes_)
    model = Sequential([
        vectorizer,
        Embedding(input_dim=vocab_size, output_dim=EMBEDDING_DIM, mask_zero=True),
        Bidirectional(LSTM(LSTM_UNITS, return_sequences=False)),
        Dropout(0.40),
        Dense(128, activation="relu"),
        BatchNormalization(),
        Dropout(0.30),
        Dense(num_classes, activation="softmax"),
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.summary()

    callbacks = [
        EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=1, min_lr=1e-6, verbose=1),
        ModelCheckpoint(MODEL_PATH, monitor="val_accuracy", save_best_only=True, verbose=1),
    ]

    print("\nStarting training...\n")
    model.fit(
        train_dataset,
        validation_data=val_dataset,
        epochs=EPOCHS,
        callbacks=callbacks,
        class_weight=class_weight_dict,
    )

    print("\nEvaluating on in-distribution test split (same generation process as training)...")
    test_loss, test_accuracy = model.evaluate(test_dataset)
    print("Test Loss     :", test_loss)
    print("Test Accuracy :", test_accuracy)
    print("NOTE: this number is NOT the final result - see EVAL.md for the held-out evaluation.")

    probabilities = model.predict(tf.constant(X_test.tolist(), dtype=tf.string), batch_size=BATCH_SIZE, verbose=1)
    predictions = np.argmax(probabilities, axis=1)

    print("\nCLASSIFICATION REPORT (in-distribution test split)")
    print(classification_report(y_test, predictions, target_names=label_encoder.classes_, digits=4))

    print("\nCONFUSION MATRIX (in-distribution test split)")
    print(confusion_matrix(y_test, predictions))

    with open(LABEL_ENCODER_PATH, "wb") as f:
        pickle.dump(label_encoder, f)

    with open(VOCAB_PATH, "wb") as f:
        pickle.dump(vectorizer.get_vocabulary(), f)

    print(f"\nSaved model to {MODEL_PATH}")
    print(f"Saved label encoder to {LABEL_ENCODER_PATH}")
    print(f"Saved vocabulary to {VOCAB_PATH}")


if __name__ == "__main__":
    main()
