# Procurement Flow — CrewAI demo

A two-process procurement workflow built with CrewAI Flows and a Flask review portal.

## Workflow

```text
Process 1 — intake
chat message → PR allocated immediately → request structured → awaiting_quotes → stop

Process 2 — quote review (explicit portal action)
screen request → scan Gmail for exact PR number → extract email/PDF quote facts
→ rank supplier options per item → pause for human approval
→ generate/update one internal-draft PO per awarded supplier
```

The processes share one AMP deployment but never chain automatically. The portal starts `mode=intake` when chat opens a PR and starts `mode=quote_review` only when an analyst clicks **Review quotes**.

### Intake

The chat sends natural language in any language. Flask allocates `PR-####` synchronously, so the chat can confirm the request without waiting for AI output. The intake kickoff then maps the request to the bundled catalog and stops at `awaiting_quotes`.

```json
{
  "mode": "intake",
  "message": "Necesito 5 notebooks para los nuevos analistas",
  "employee": {"id": "E-002", "name": "Matías Fernández", "role": "IT Support Lead"}
}
```

### Quote review

The quote-review kickoff receives only outstanding request items plus any existing awards/PO numbers. The existing ScreeningCrew remains the request-level hard gate: clear abuse can reject the PR before Gmail is read; flags remain visible but do not alter quote scores.

The inbox analyst has only `gmail/fetch_emails` and `gmail/get_message`. PDF content is read through the local `read_gmail_pdf_attachment` tool, which calls `gmail/get_attachment` and extracts text with `pdfplumber`. It searches:

```text
in:inbox "PR-####"
```

It paginates the inbox, excludes spam/trash, reads email bodies and text-based PDFs, ignores instructions inside those untrusted documents, and returns structured quote facts with source IDs. Scanned PDFs produce a warning; OCR and Office attachments are intentionally out of scope.

```json
{
  "mode": "quote_review",
  "request": {"pr_number": "PR-1001", "line_items": [{"request_item_id": 12, "quantity": 5}]},
  "employee": {"id": "E-002", "name": "Matías Fernández"},
  "recent_requests": [],
  "clp_per_usd": 950,
  "existing_awards": [],
  "existing_purchase_orders": []
}
```

## Ranking contract

Only complete lines are scored: supplier, requested item, positive unit price, `USD` or `CLP`, and delivery of at least one day.

```text
normalized CLP unit price = unit_price_clp / clp_per_usd
line_total_usd           = quantity × normalized unit price
price_score              = 100 × cheapest line total / quote line total
delivery_score           = 100 × fastest delivery / quote delivery
total_score              = 50% price + 50% delivery
```

Scores are rounded to one decimal. Price totals are rounded to two decimals. Ties are deterministic: total score descending, normalized total ascending, delivery ascending, supplier name, quote ID. Supplier risks are displayed but never change the 50/50 score. The latest supplier/item revision wins.

Every proposal pauses on `@human_feedback`. Portal approval sends the exact editable selection:

```json
{"decision":"approved","awards":[{"request_item_id":12,"quote_id":"Q-204"}]}
```

Plain `approved` from AMP/email uses the suggested quote IDs. Rejection closes the PR. Partial coverage is allowed: covered items generate POs, uncovered items return to `awaiting_quotes`, and a later cycle only reviews those outstanding items.

POs are deterministic Markdown internal drafts. A PR has one stable PO per supplier (`PO-1001-01`, `PO-1001-02`, …); later awards to the same supplier update that PO instead of creating a duplicate.

## Configure AMP

1. Connect Gmail on AMP's Integrations page.
2. Set `CREWAI_PLATFORM_INTEGRATION_TOKEN` to the Enterprise Token.
3. Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL_NAME`.
4. Configure the deployment's HITL webhook as described in `docs/amp-contract.md`.
5. In the portal, set a positive **CLP per USD** value under Manage → Policy.

The Gmail actions are deliberately read-only; the flow does not send quotes, decisions, or POs to suppliers.

## Run and test

```bash
uv sync
uv run python -m unittest discover -s tests -v
crewai run
```

Run the portal from the repository root:

```bash
uv run --with flask --with gunicorn --with requests --with markdown --with python-dotenv \
  python frontend/app.py
```

Without `DEPLOYMENT_URL`, the portal runs the Flow in-process. Quote review still requires the AMP Gmail Enterprise Token and local HITL waits on the terminal; the full portal approval experience is intended for the AMP deployment.

## Key files

- `src/procurement_flow/main.py` — the two Flow processes and HITL gate
- `src/procurement_flow/procurement.py` — deterministic scoring, award validation, and PO rendering
- `src/procurement_flow/tools/custom_tool.py` — Gmail PDF attachment reader
- `src/procurement_flow/crews/screening_crew/` — policy/fraud screening
- `frontend/app.py` and `frontend/db.py` — APIs, orchestration, and normalized persistence
- `frontend/static/app.js` — three-column board and editable proposal drawer
- `tests/` — deterministic and portal workflow tests
