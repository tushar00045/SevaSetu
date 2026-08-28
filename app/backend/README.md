# SevaSetu Backend

Express + TypeScript API for grievance ingestion, confidence-gated auto-routing,
duplicate detection, and SLA tracking.

## Run it

Needs the model service running first (see `../model_service/README.md`) —
`index.ts` calls it at `http://localhost:8000` by default, and there's no
fallback if it's unreachable.

```bash
npm install
npm run seed   # optional: populate with 15 realistic sample complaints (uses StubClassifier, not the model)
npm run dev    # starts on http://localhost:4000
```

## Key files

- `src/classifier.ts` — the classifier interface. `index.ts` uses
  `RemoteClassifier`, which calls the model service (see
  `../model_service/README.md`; the retrained BiLSTM models it serves are
  documented in the SevaSetu repo's `CLAUDE_CODE_BRIEF.md` and `EVAL.md`).
  `StubClassifier`, the original transparent keyword-rule classifier, is
  kept around for `seed.ts` so demo data can be generated without the model
  service running.
- `src/routing.ts` — the actual "smart re-router": confidence-gated
  auto-route vs. human-review, SLA deadline calculation, mandatory
  resolution notes on every status change (this is the direct fix for the
  "resolved without action" finding cited in the pitch deck).
- `src/duplicates.ts` — token-overlap duplicate detection. Marked as a
  placeholder for real embedding-based (IndicSBERT) similarity.
- `src/db.ts` — SQLite schema. Two tables: `tickets` and `ticket_events`
  (the audit trail).

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/complaints` | Citizen submits a complaint; gets classified and routed |
| GET | `/api/tickets` | List tickets, filterable by `status`, `department`, `urgency` |
| GET | `/api/tickets/:id` | Ticket detail + full audit trail |
| PATCH | `/api/tickets/:id/status` | Officer updates status (note required) |
| GET | `/api/stats` | Dashboard summary counts |

## Config

The auto-route confidence threshold (default 0.6) and SLA windows by urgency
are in `src/routing.ts`. Tune these to match whatever your retrained
classifier's real confidence distribution looks like.
