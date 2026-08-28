# SevaSetu model service

FastAPI wrapper around the retrained department and urgency BiLSTM
classifiers. See `../../CLAUDE_CODE_BRIEF.md` for why they needed retraining
and `../../EVAL.md` for honest held-out accuracy, department 76.39%, urgency
57.14%, neither is 100% and both still make specific, documented mistakes.

## Run it

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --port 8000
```

Check it came up: `curl http://localhost:8000/health` should return
`{"ok":true}`.

## What's here

- `app.py` — loads the two `.keras` models and their label encoders once at
  startup, exposes `POST /classify`. It reads them straight from the repo
  root (`../../sevasetu_department_bilstm.keras` etc.), not a local copy, so
  retraining with `../../train_department_model.py` /
  `../../train_urgency_model.py` and restarting this service is the whole
  update flow.

## API

`POST /classify`

Request: `{"text": "complaint text"}`

Response, exactly the shape `RemoteClassifier` in `backend/src/classifier.ts`
expects:

```json
{
  "department": "Police Department",
  "departmentConfidence": 0.999,
  "urgency": "high",
  "urgencyConfidence": 0.999
}
```

## Who calls this

`backend/src/index.ts` constructs a `RemoteClassifier` pointed at
`http://localhost:8000` by default (override with the `CLASSIFIER_URL` env
var). The backend has no fallback if this service isn't reachable, start
this before the backend.
