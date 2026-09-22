# Prompt Guard — Frontend (Raima's part)

React + Tailwind client for the Prompt Guard security gateway. Sends prompts to
the backend's `POST /scan` endpoint and displays the risk score, decision,
threats and signals it returns — per the Shared Contract in the handoff doc.

## Setup

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on `http://localhost:5173` and expects the backend at
`http://localhost:8000` (override with a `VITE_API_BASE_URL` env var / `.env`
file if Neha's backend runs elsewhere).

## Structure

```
src/
├── components/   # Presentational pieces (badge, gauge, chips, log table, ...)
├── pages/
│   ├── ScannerPage.jsx     # Prompt input + live scan result
│   └── DashboardPage.jsx   # Stats + searchable/filterable event log
└── services/
    ├── api.js        # The ONLY file that calls the backend (POST /scan)
    └── mockData.js    # Mock responses, used only when the backend is unreachable
```

## Contract rules this code follows

- Only sends `{ "prompt": "..." }` to `POST /scan` — never renames the field.
- Never computes `risk_score` or the `ALLOW` / `SANITIZE` / `BLOCK` decision
  itself — those always come from the backend response.
- Displays `signals[]`, `threats[]`, and `pii[]` exactly as returned, using
  the exact strings defined in the contract (no relabeling like "Blocked").
- Shows `sanitized_prompt` only when it isn't `null`.
- Shows a loading state while `/scan` is in flight and a clear, actionable
  error (with a link to preview mock data) if the backend can't be reached.

## Notes for the team

- The Dashboard page tries `GET /events` first (not yet part of the Micro
  Project contract) and falls back to mock data if that endpoint doesn't
  exist yet. If we add a real log-listing endpoint, update the fetch in
  `DashboardPage.jsx` — and, per the handoff doc, agree the new endpoint with
  Neha and Lakshita first.
- Design direction: dark "monitoring console" look, with the traffic-light
  Allow/Sanitize/Block palette from the synopsis's Section 5.5 table driving
  every status color in the UI, and a monospace face reserved for actual
  score/signal data (not just for decoration).
