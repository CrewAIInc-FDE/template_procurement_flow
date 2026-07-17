# Procurement Demo Portal (frontend)

Flask portal for the ProcurementFlow AMP demo: chat widget → kanban board → live HITL
approval. Contract in `../docs/frontend-plan.md` + `../docs/amp-contract.md`.

## Run locally

```bash
# from the repo root
uv run --with flask --with gunicorn --with requests --with markdown --with python-dotenv \
  python frontend/app.py            # http://localhost:5001
```

Two backends, picked by env:

- **`DEPLOYMENT_URL` set** (in `frontend/.env`, with `DEPLOYMENT_KEY` + `WEBHOOK_TOKEN`):
  kickoffs go to the AMP deployment. Results arrive via webhook (needs `PUBLIC_BASE_URL`
  reachable from AMP) *and* a status-polling watchdog — locally, polling alone is enough.
- **`DEPLOYMENT_URL` unset**: ProcurementFlow runs in-process from `../src`
  (needs `OPENAI_API_KEY`, read from `../.env`). **Caveat:** escalated requests block on a
  console `approved`/`rejected` prompt in the server terminal — there is no HITL webhook
  locally, so the board's Approve/Reject buttons and the `awaiting review` badge only work
  against a real AMP deployment.

## Fixtures (instant UI states, zero LLM calls)

```bash
rm -f frontend/portal.db
cd frontend && uv run --with flask --with requests --with markdown --with python-dotenv \
  flask demo-fixtures
```

Replays `../docs/examples/*.json` through the real envelope pipeline: PR-1001
approved+PO, PR-1002 awaiting review (alerts + memo + no-op Approve/Reject),
PR-1003 rejected. Dev-only — `docs/` is gitignored and absent from deploys.

## Deploy (Heroku)

Repo root has its own `uv.lock` (the AMP deployment), so Heroku must only ever see
`frontend/` — deploy the subtree, never the repo root:

```bash
heroku create <app>
heroku config:set DEPLOYMENT_URL=... DEPLOYMENT_KEY=... WEBHOOK_TOKEN=... \
                  PUBLIC_BASE_URL=https://<app>.herokuapp.com
git push heroku "$(git subtree split --prefix frontend <branch>)":main --force
```

Then, once per deployment, in AMP's HITL settings: webhook URL
`https://<app>.herokuapp.com/api/hitl-webhook?token=<WEBHOOK_TOKEN>` + reviewer email.

SQLite lives on the dyno's ephemeral filesystem: it reseeds from `seed_data/` on every
restart and requests vanish — fine between demo runs (upgrade path: Heroku Postgres).
