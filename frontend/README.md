# Procurement Portal

Flask portal for the two-process ProcurementFlow AMP demo.

## Lifecycle

1. Chat creates a placeholder PR and immediately returns its `PR-####` number.
2. Intake structures and screens the request, sends supplier RFQs through Composio Gmail, and stops at `awaiting_quotes`.
3. An analyst clicks **Review quotes**; `POST /api/requests/<pr>/review-quotes` starts one idempotent `mode=quote_review` kickoff.
4. The card moves through `reviewing_quotes` → `awaiting_review`.
5. The drawer shows an editable per-item proposal. Approval forwards structured award JSON to the AMP HITL callback.
6. The final envelope persists awards and one stable PO per supplier. Partial coverage returns the PR to `awaiting_quotes`; complete coverage moves it to `approved`.

Board columns:

- Processing: `submitted`, `rfq_failed`
- Awaiting Quotes: `awaiting_quotes`
- Quote Review: `reviewing_quotes`, `awaiting_review`
- Complete: `approved`, `rejected`

## Run locally

```bash
cp frontend/.env.example frontend/.env
uv run --with flask --with gunicorn --with requests --with markdown --with python-dotenv \
  python frontend/app.py
```

With `DEPLOYMENT_URL` configured, the app uses AMP kickoff/status/webhook transport. Without it, it imports `ProcurementFlow` from `../src`; Gmail still needs `COMPOSIO_API_KEY`, `COMPOSIO_USER_ID`, and a connected Composio account, while local HITL waits for terminal input.

The Manage → Policy setting `clp_per_usd` is required and must be positive before quote review can start. Scoring weights are fixed at 50% price and 50% delivery.

## API

- `POST /api/requests` — create PR and start intake
- `POST /api/requests/<pr>/review-quotes` — explicit/idempotent quote-review kickoff
- `POST /api/requests/<pr>/retry-rfqs` — retry an intake whose supplier sends all failed
- `GET /api/requests` / `GET /api/requests/<pr>` — board/detail, including RFQ/reply tracking, outstanding items, quote review, warnings, and `purchase_orders[]`
- `POST /api/requests/<pr>/approve` — `{awards:[{request_item_id, quote_id}]}`
- `POST /api/requests/<pr>/reject` — reject the whole PR
- `POST /api/webhook/<pr>` — Flow events
- `POST /api/hitl-webhook` — structured proposal + callback URL from AMP
- `GET|PATCH /api/settings` — `clp_per_usd`

SQLite is intentionally ephemeral on Heroku. `rfq_dispatches` tracks intended/actual recipients and Gmail thread/reply state. The normalized `purchase_orders` and `purchase_order_items` tables enforce one PO per PR/supplier and one award per request item.

## Deploy

Deploy only the `frontend/` subtree, then configure:

```text
DEPLOYMENT_URL
DEPLOYMENT_KEY
WEBHOOK_TOKEN
PUBLIC_BASE_URL
CLP_PER_USD
```

Set the AMP HITL webhook to:

```text
https://<portal>/api/hitl-webhook?token=<WEBHOOK_TOKEN>
```
