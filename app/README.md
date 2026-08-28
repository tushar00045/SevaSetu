# SevaSetu

AI-based grievance triage and auto-routing system for government service portals.
SIH 2026 — Problem Statement SW-09 — Team Parity

## What this is

A working backend + frontend for the "smart re-router" architecture described
in the pitch deck: complaints get classified, confidence-gated auto-routing
sends high-confidence cases straight to the right department with an SLA
clock, low-confidence cases go to human review (never silently auto-closed),
and near-duplicate complaints are flagged rather than creating redundant
tickets.

## Status of the ML model

**Read this before demoing.** The original BiLSTM classifier (`NLPClassifier`
repo) reported 100% test accuracy, which was a red flag, not a result — it
was trained on templated synthetic data with only 367 unique tokens, so it
learned dataset shortcuts, not language. It misrouted genuinely novel text
(a shooting/murder complaint was classified as "State Pollution Control
Board" at 96% confidence when independently tested).

That model has since been retrained on a diversified, mostly non-templated
dataset (see `../CLAUDE_CODE_BRIEF.md` at the repo root for the diagnosis and
`../EVAL.md` for honest held-out metrics, including every case it still gets
wrong). It is now wired into this backend via `RemoteClassifier`
(`backend/src/classifier.ts`), which calls a small FastAPI service in
`model_service/` that loads the retrained `.keras` models straight from the
repo root, no copy to keep in sync. The murder/shooting example above now
routes to Police Department at ~100% confidence, and the same case from the
brief that was a 38%-confidence guess for a theft complaint is now a
confident correct prediction.

Held-out results, not the inflated in-distribution number: department
classifier 76.39% accuracy / 0.78 macro-F1, urgency classifier 57.14%
accuracy / 0.38 macro-F1. Urgency in particular still defaults to "medium"
on severity language it wasn't trained on — read `EVAL.md` before treating
either number as more solid than it is. `StubClassifier` (the original
transparent keyword-rule classifier) is kept in `classifier.ts` and is still
used by `npm run seed` to generate demo data without needing the model
service running.

## Quick start

One command from the repo root starts all three and stops them together on
Ctrl+C:

```bash
./run.sh
```

It sets up each piece's virtual env / `node_modules` on first run (the
model service's TensorFlow install takes a few minutes the first time),
then starts the model service, waits for it to answer `/health`, and starts
the backend and frontend. See `../run.sh` for what it actually runs, it's
short.

To run the three pieces by hand instead, in three terminals:

```bash
# Terminal 1 — model service (department + urgency classifiers)
cd model_service && python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --port 8000

# Terminal 2 — backend
cd backend && npm install && npm run seed && npm run dev

# Terminal 3 — frontend
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 for the officer dashboard, or
http://localhost:5173/track for the citizen-facing form.

The backend expects the model service at `http://localhost:8000` by default;
set `CLASSIFIER_URL` to point elsewhere. If the model service isn't running,
`/api/complaints` will fail since `RemoteClassifier` has no fallback — start
it first (or just use `run.sh`, which handles the ordering).

## Structure

```
backend/         Express + TypeScript API, SQLite, routing/duplicate/SLA logic
frontend/        React + Vite, officer dashboard + citizen tracker
model_service/   FastAPI wrapper around the .keras models at the repo root
```

See each folder's README for details.
