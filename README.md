# Procurement Flow — CrewAI demo

A two-process procurement workflow built with CrewAI Flows and a Flask review portal.

## Workflow

```text
Process 1 — intake and supplier outreach
chat message → PR allocated → request structured → screen request
→ match suppliers by catalog category → send one Gmail RFQ per supplier → awaiting_quotes

Process 2 — quote review (explicit portal action)
scan Gmail for replies to recorded RFQs → extract email/PDF quote facts
→ rank supplier options per item → pause for human approval
→ generate/update one internal-draft PO per awarded supplier
```

The processes share one AMP deployment but never chain automatically. The portal starts `mode=intake` when chat opens a PR and starts `mode=quote_review` only when an analyst clicks **Review quotes**.

### Intake

The chat sends natural language in any language. Flask allocates `PR-####` synchronously, so the chat can confirm the request without waiting for AI output. Intake maps the request to the bundled catalog, screens it, selects suppliers by category, and sends an RFQ from the Gmail account connected through Composio. Rejected requests never contact suppliers.

```json
{
  "mode": "intake",
  "message": "Necesito 5 notebooks para los nuevos analistas",
  "employee": {"id": "E-002", "name": "Matías Fernández", "role": "IT Support Lead"},
  "request": {"pr_number": "PR-1001"},
  "recent_requests": []
}
```

Each email has a stable reference such as `RFQ-PR-1001-S-005`. Before sending, the flow searches Gmail Sent for that reference so a retried kickoff does not duplicate the message. Set `DEMO_RFQ_RECIPIENT_OVERRIDE` to route every supplier email to one personal demo mailbox while retaining the intended supplier identity in the portal.

### Quote review

The quote-review kickoff receives outstanding request items, existing awards/PO numbers, and the RFQ dispatch records created during intake. Screening has already happened before supplier outreach; flags remain visible but do not alter quote scores.

The inbox analyst has only `GMAIL_FETCH_EMAILS` and `GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID`. PDF content is read through the local `read_gmail_pdf_attachment` tool, which calls `GMAIL_GET_ATTACHMENT` and extracts text with `pdfplumber`. For each recorded RFQ it searches:

```text
in:inbox -from:me from:<actual-recipient> "RFQ-PR-####-S-###"
```

It paginates the inbox, excludes spam/trash and the original sent message, verifies the stored Gmail thread, reads email bodies and text-based PDFs, ignores instructions inside those untrusted documents, and returns structured quote facts with source IDs. Supplier identity comes from the RFQ record, so multiple demo replies from one personal mailbox remain distinct. Scanned PDFs produce a warning; OCR and Office attachments are intentionally out of scope.

```json
{
  "mode": "quote_review",
  "request": {"pr_number": "PR-1001", "line_items": [{"request_item_id": 12, "quantity": 5}]},
  "employee": {"id": "E-002", "name": "Matías Fernández"},
  "recent_requests": [],
  "clp_per_usd": 950,
  "rfq_dispatches": [{"rfq_id": "RFQ-PR-1001-S-005", "actual_recipient": "demo@example.com", "gmail_thread_id": "thread-1", "status": "sent"}],
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

1. In [Composio](https://platform.composio.dev), connect the Gmail account under a stable user ID such as `procurement-demo`.
2. Set `COMPOSIO_API_KEY` and set `COMPOSIO_USER_ID` to that exact user ID on the AMP deployment.
3. Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL_NAME`.
4. For the demo, set `DEMO_RFQ_RECIPIENT_OVERRIDE` to a mailbox different from the connected sending account.
5. Configure the deployment's HITL webhook as described in `docs/amp-contract.md`.
6. In the portal, set a positive **CLP per USD** value under Manage → Policy.

Supplier seed addresses use the reserved `.example` domain and cannot receive live mail without the demo override. Replace them with real supplier contacts before disabling the override. Decisions and POs remain internal and are not emailed.

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

Without `DEPLOYMENT_URL`, the portal runs the Flow in-process. Quote review still requires `COMPOSIO_API_KEY`, `COMPOSIO_USER_ID`, and a connected Gmail account; local HITL waits on the terminal. The full portal approval experience is intended for the AMP deployment.

## Key files

- `src/procurement_flow/main.py` — the two Flow processes and HITL gate
- `src/procurement_flow/procurement.py` — deterministic scoring, award validation, and PO rendering
- `src/procurement_flow/tools/custom_tool.py` — Gmail PDF attachment reader
- `src/procurement_flow/crews/screening_crew/` — policy/fraud screening
- `frontend/app.py` and `frontend/db.py` — APIs, orchestration, and normalized persistence
- `frontend/static/app.js` — three-column board and editable proposal drawer
- `tests/` — deterministic and portal workflow tests
