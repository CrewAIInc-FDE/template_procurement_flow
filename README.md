# Procurement Flow — CrewAI demo (HPE & Nvidia event, Santiago + Global customer)

An AI procurement pipeline built with [CrewAI](https://crewai.com) Flows, deployed on **CrewAI AMP**. An employee types a free-text purchase request into a portal (any language); the flow matches it to the item catalog, screens it against procurement policy, detects fraud/anomaly patterns, sources the best supplier, and either auto-drafts a purchase order or escalates to a human — who approves it from a kanban board.

## The pipeline (one flow, three modes)

```
mode=intake      raw message ──► LLM extraction ──► structured request draft (line items, total, urgency)
mode=triage      request ──► Screening Crew (policy compliance + fraud/anomaly)
                           ──► reject? ──► rejection note
                           ──► Sourcing Crew (cost analyst + risk analyst + procurement manager)
                           ──► flagged or over limit? ──► escalation memo ──► ⏸ PAUSED for human review
                           │        (AMP HITL: email / dashboard / webhook — SLA metrics tracked)
                           │        reviewer replies "approved" ──► purchase order
                           │        reviewer replies "rejected" ──► rejection note w/ reviewer comments
                           ──► else ──► purchase order (auto-approved)
```

- **Screening Crew**: `policy_compliance_officer` checks the approval matrix, requester limits, category and conduct rules; `fraud_anomaly_analyst` hunts order splitting, implausible quantities, personal-use purchases.
- **Sourcing Crew**: compares supplier offers on total cost of ownership, checks vendor history and sourcing rules (ISO certs, on-time rate, advance-payment limits), awards one supplier with a runner-up.
- Reference data lives in `data/` and ships with the deployment: 29 catalog items (IT/office, PPE, industrial spares, services & software), 7 suppliers with personalities (a solid incumbent, a local Chilean up-and-comer, a premium German vendor, a sketchy trading company…), 85 offers, and the procurement policy.

## Modes & AMP inputs

One deployment, one flow, two modes. The `mode` input selects the path; every kickoff returns the same flat envelope (all output fields present, unused ones empty). Reference data (catalog, suppliers, offers, policy) is bundled — never send it.

### `mode: "intake"` — parse a free-text request (~10s)

Turns whatever the employee typed (any language) into a structured request draft: line items matched to real catalog ids, quantities inferred from the text, prices/totals recomputed from the catalog (LLM math is never trusted), anything unmatchable listed in `unmatched`, plus `justification`, `urgency`, and `detected_language`.

```json
{
  "mode": "intake",
  "message": "Necesito 5 notebooks estándar y 5 monitores para los nuevos analistas.",
  "employee": {"id": "E-002", "name": "Matías Fernández", "role": "IT Support Lead",
               "department": "Information Technology", "approval_limit_usd": 25000}
}
```

Reads from the result: `request_draft` (line_items, estimated_total_usd, urgency, unmatched, detected_language), `final_status: "submitted"`.

### `mode: "triage"` — screen, source, route, and (if needed) wait for a human

Runs the full pipeline on a submitted request. The **Screening Crew** checks policy (approval matrix, requester limit, order splitting vs `recent_requests`, category and conduct rules) and hunts anomalies; a conduct violation or clear abuse → **rejected** with a rejection note. Otherwise the **Sourcing Crew** compares the bundled supplier offers on total cost of ownership and vendor risk, and awards one supplier.

If screening flagged anything OR the sourcing total exceeds `AUTO_APPROVE_LIMIT_USD`, the flow writes an escalation memo and **pauses on a `@human_feedback` gate** — AMP's HITL management takes over: the Procurement Manager gets the memo by email (reply "approved"/"rejected" directly), in the AMP dashboard, or via the HITL webhook, and **AMP tracks approval SLA metrics** for the pending review. Free-form replies are collapsed to an outcome by an LLM, and the reviewer's comments are recorded. On "approved" the flow resumes into PO generation; on "rejected" it writes a rejection note quoting the reviewer. Clean requests under the limit skip the pause entirely → **approved** with an auto-generated PO. The kickoff's `flow_finished`/status result therefore arrives only after any review is resolved.

```json
{
  "mode": "triage",
  "request": {"pr_number": "PR-1002", "line_items": [...], "justification": "...",
              "urgency": "high", "unmatched": [], "estimated_total_usd": 195600.0,
              "requested_by": "Valentina Rojas"},
  "employee": {"id": "E-001", "name": "Valentina Rojas", "role": "Maintenance Superintendent",
               "approval_limit_usd": 75000},
  "recent_requests": []
}
```

(`request` = the intake `request_draft` plus `pr_number` and `requested_by` — the caller assigns PR numbers. `recent_requests` = same employee, last 14 days, for order-splitting detection; `[]` if none.)

Reads from the result: `final_status` (`approved` | `rejected` — reviews resolve before the flow finishes, so `needs_review` is never terminal), `screening` (verdict, violations, anomalies, reasoning), `sourcing` (null if rejected before sourcing), `po_md` or `rejection_md`, `escalation_md` (kept when the request went through review), and `alerts[]` (`{severity, message}` per finding).

While a review is pending, the memo and response channel are delivered through AMP's HITL surfaces (`new_request` webhook payload carries the content and a `callback_url` — POST `{"feedback": "approved"}` to it to respond programmatically, e.g. from a board button).

## Run locally

```bash
# .env needs OPENAI_API_KEY
crewai install
crewai run          # smoke run: Spanish laptop request → intake → triage → auto-approved PO
```

Try other scenarios by kicking off modes directly (input shapes above):

```bash
uv run python -c "
from procurement_flow.main import ProcurementFlow
import json
r = ProcurementFlow().kickoff(inputs={'mode': 'intake', 'message': 'I urgently need 12 slurry pumps and 12 maintenance contracts for the concentrator plant', 'employee': {'id': 'E-001', 'name': 'Valentina Rojas', 'role': 'Maintenance Superintendent', 'approval_limit_usd': 75000}})
print(json.dumps(r['request_draft'], indent=2))
"
```

## Demo script (suggested)

1. **Happy path (ES):** "Necesito 5 notebooks y 5 monitores para los nuevos analistas" from the IT lead → clean screening → local supplier wins on TCO → auto-approved PO. Shows: multilingual intake, catalog matching, policy-aware sourcing.
2. **Human in the loop:** 12 slurry pumps + maintenance contracts (~USD 195k) from the superintendent → over the USD 150k auto-limit → flow pauses on AMP's HITL gate → presenter shows the pending review + **approval SLA metrics in AMP**, replies "approved" (email reply or dashboard, or the board's Approve button via `callback_url`) → flow resumes, PO generates live.
3. **The catch:** 30 laptops "as end-of-year gifts for my team" from a junior analyst → conduct-rule violation + role-limit breach + implausible quantity → rejected with alerts.

## Deploy on AMP

Repo root is the deployable flow project (`procurement_flow.main:kickoff`). Connect the repo in AMP, set env vars (`OPENAI_API_KEY`, optional `OPENAI_MODEL_NAME`, `AUTO_APPROVE_LIMIT_USD`), deploy. Kickoff inputs per mode are documented above; transport details (webhooks, status polling, wakeup) live in `docs/amp-contract.md` (local-only, gitignored) along with real result envelopes in `docs/examples/`.

## Where things live

- `src/procurement_flow/main.py` — the Flow (mode router, intake, triage pipeline, PO generation)
- `src/procurement_flow/crews/screening_crew/` + `sourcing_crew/` — agents & tasks (YAML) + crew classes
- `src/procurement_flow/types.py` — shared Pydantic models (RequestDraft, ScreeningResult, SourcingRecommendation)
- `data/seed/*.json` — catalog, suppliers, offers, employees (also seeds the frontend's SQLite)
- `data/procurement_policy.md` — the policy the screening crew enforces
- `docs/` — (local-only, gitignored) frontend ↔ AMP contract, frontend plan, example result envelopes
- `frontend/` — (next pass) Flask portal on Heroku: chat widget + kanban board
