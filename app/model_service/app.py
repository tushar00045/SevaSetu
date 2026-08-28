"""
SevaSetu model-serving endpoint.

Loads the retrained department + urgency BiLSTM classifiers (see
CLAUDE_CODE_BRIEF.md / EVAL.md at the repo root for how they were trained
and what their honest accuracy is) and exposes a single POST /classify route
that returns exactly the shape `RemoteClassifier` in
backend/src/classifier.ts expects:

    { department, departmentConfidence, urgency, urgencyConfidence }

Run:
    uvicorn app:app --port 8000

Then point RemoteClassifier at http://localhost:8000 (see classifier.ts).
"""

import pickle
from pathlib import Path

import numpy as np
import tensorflow as tf
from fastapi import FastAPI
from pydantic import BaseModel
from tensorflow.keras.models import load_model

# Model files live at the repo root (not copied here) so retraining and
# restarting this service is the whole update flow, nothing to keep in
# sync by hand. app.py -> model_service/ -> app/ -> repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(title="SevaSetu classifier service")

department_model = load_model(REPO_ROOT / "sevasetu_department_bilstm.keras")
with open(REPO_ROOT / "department_label_encoder.pkl", "rb") as f:
    department_encoder = pickle.load(f)

urgency_model = load_model(REPO_ROOT / "sevasetu_urgency_bilstm.keras")
with open(REPO_ROOT / "urgency_label_encoder.pkl", "rb") as f:
    urgency_encoder = pickle.load(f)


class ClassifyRequest(BaseModel):
    text: str


class ClassifyResponse(BaseModel):
    department: str
    departmentConfidence: float
    urgency: str
    urgencyConfidence: float


def predict_one(model, label_encoder, text: str):
    input_tensor = tf.constant([text], dtype=tf.string)
    probabilities = model.predict(input_tensor, verbose=0)[0]
    predicted_index = int(np.argmax(probabilities))
    label = label_encoder.inverse_transform([predicted_index])[0]
    confidence = float(probabilities[predicted_index])
    return label, confidence


@app.post("/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest):
    department, department_confidence = predict_one(department_model, department_encoder, req.text)
    urgency, urgency_confidence = predict_one(urgency_model, urgency_encoder, req.text)
    return ClassifyResponse(
        department=department,
        departmentConfidence=department_confidence,
        urgency=urgency,
        urgencyConfidence=urgency_confidence,
    )


@app.get("/health")
def health():
    return {"ok": True}
