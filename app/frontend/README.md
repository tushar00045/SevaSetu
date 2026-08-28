# SevaSetu Frontend

React + TypeScript + Vite. Two audiences, two screens:

- **Officer dashboard** (`/`) — urgency-sorted queue, filters, per-ticket
  confidence meter with a visible auto-route threshold marker, mandatory
  resolution-note status updates, full audit trail.
- **Citizen tracker** (`/track`) — plain-language complaint submission and
  status check. No department jargon, no confidence scores — written for
  the person filing the complaint, not the officer.

## Run it

```bash
npm install
npm run dev   # starts on http://localhost:5173, expects backend on :4000
```

Run the backend first (see `../backend/README.md`) — the dashboard shows
an inline error if it can't reach the API rather than failing silently.

## Design notes

The visual direction is deliberately an institutional ledger/register look
(paper background, ink text, a single seal-green accent) rather than a
generic SaaS dashboard — see `src/tokens.css` for the full token system and
the reasoning in code comments. If Google Fonts is blocked on your network,
it falls back to system serif/sans-serif; layout doesn't break either way.
