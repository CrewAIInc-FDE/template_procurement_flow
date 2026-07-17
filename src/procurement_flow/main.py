#!/usr/bin/env python
import json
import os
from pathlib import Path

from pydantic import BaseModel

from crewai import LLM
from crewai.flow import Flow, human_feedback, listen, or_, router, start

from procurement_flow.crews.screening_crew.screening_crew import ScreeningCrew
from procurement_flow.crews.sourcing_crew.sourcing_crew import SourcingCrew
from procurement_flow.types import (
    RequestDraft,
    ScreeningResult,
    SourcingRecommendation,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
# Policy approval matrix: sourcing totals above this need Finance Director review.
AUTO_APPROVE_LIMIT_USD = float(os.getenv("AUTO_APPROVE_LIMIT_USD", "150000"))

# Reference data ships with the deployment; kickoff inputs may override it.
HEAVY_INPUT_FIELDS = {
    "catalog",
    "suppliers",
    "supplier_offers",
    "policy_md",
    "recent_requests",
}


class ProcurementState(BaseModel):
    # --- kickoff inputs ---
    mode: str = "intake"  # intake | triage
    message: str = ""  # intake: raw text from the portal widget
    employee: dict = {}
    request: dict = {}  # triage: the PR (pr_number, line_items, ...)
    recent_requests: list = []  # triage: same employee, last 14 days
    catalog: list = []  # optional overrides of the bundled reference data
    suppliers: list = []
    supplier_offers: list = []
    policy_md: str = ""
    auto_approve_limit_usd: float = AUTO_APPROVE_LIMIT_USD
    # --- outputs ---
    request_draft: RequestDraft | None = None
    screening: ScreeningResult | None = None
    sourcing: SourcingRecommendation | None = None
    final_status: str = ""  # submitted | needs_review | approved | rejected
    po_md: str = ""
    escalation_md: str = ""
    rejection_md: str = ""
    alerts: list[dict] = []


class ProcurementFlow(Flow[ProcurementState]):

    @start()
    def receive(self):
        """Load bundled reference data for anything the caller didn't send."""
        if not self.state.catalog:
            self.state.catalog = json.loads(
                (DATA_DIR / "seed" / "catalog_items.json").read_text()
            )
        if not self.state.suppliers:
            self.state.suppliers = json.loads(
                (DATA_DIR / "seed" / "suppliers.json").read_text()
            )
        if not self.state.supplier_offers:
            self.state.supplier_offers = json.loads(
                (DATA_DIR / "seed" / "supplier_offers.json").read_text()
            )
        if not self.state.policy_md:
            self.state.policy_md = (DATA_DIR / "procurement_policy.md").read_text()

    @router(receive)
    def dispatch(self):
        return self.state.mode

    # ------------------------------------------------------------------
    # Mode: intake — raw portal message → structured request draft
    # ------------------------------------------------------------------

    @listen("intake")
    def run_intake(self):
        draft = LLM(model=MODEL).call(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are the intake step of a procurement system. An "
                        "employee typed a free-text purchase request (any "
                        "language). Map what they ask for to catalog items.\n\n"
                        "Rules:\n"
                        "- Use ONLY catalog_item_id values that exist in the "
                        "catalog below.\n"
                        "- Infer quantities from the text (e.g. 'for 5 new "
                        "hires' means 5); default to 1 if unstated.\n"
                        "- Anything requested that has no reasonable catalog "
                        "match goes in 'unmatched' verbatim.\n"
                        "- 'justification' is a faithful 1-2 sentence summary "
                        "of the requester's stated reason, in the original "
                        "language.\n"
                        "- 'urgency' is low, normal or high based on the tone "
                        "and any deadlines mentioned.\n"
                        "- 'detected_language' is the ISO 639-1 code of the "
                        "message.\n"
                        "- Prices: copy unit_price_usd from the catalog.\n\n"
                        f"Employee:\n{json.dumps(self.state.employee)}\n\n"
                        f"Message:\n{self.state.message}\n\n"
                        f"Catalog:\n{json.dumps(self.state.catalog)}"
                    ),
                }
            ],
            response_model=RequestDraft,
        )
        if isinstance(draft, str):
            draft = RequestDraft.model_validate_json(draft)

        # Recompute prices and totals from the catalog — never trust LLM math,
        # and drop hallucinated item ids into `unmatched`.
        by_id = {c["id"]: c for c in self.state.catalog}
        items = []
        for li in draft.line_items:
            cat = by_id.get(li.catalog_item_id)
            if cat is None:
                draft.unmatched.append(li.name or li.catalog_item_id)
                continue
            li.sku = cat["sku"]
            li.name = cat["name"]
            li.unit_price_usd = cat["unit_price_usd"]
            li.line_total_usd = round(li.quantity * cat["unit_price_usd"], 2)
            items.append(li)
        draft.line_items = items
        draft.estimated_total_usd = round(sum(i.line_total_usd for i in items), 2)

        self.state.request_draft = draft
        self.state.final_status = "submitted"
        return self._envelope()

    # ------------------------------------------------------------------
    # Mode: triage — screening → sourcing → route
    # ------------------------------------------------------------------

    @listen("triage")
    def run_screening(self):
        result = (
            ScreeningCrew()
            .crew()
            .kickoff(
                inputs={
                    "pr_number": self._pr_number(),
                    "request_json": json.dumps(self.state.request, indent=2),
                    "employee_json": json.dumps(self.state.employee, indent=2),
                    "recent_requests_json": json.dumps(
                        self.state.recent_requests, indent=2
                    ),
                    "policy": self.state.policy_md,
                    "unmatched": json.dumps(
                        self.state.request.get("unmatched", [])
                    ),
                }
            )
        )
        self.state.screening = result.pydantic

    @router(run_screening)
    def screening_gate(self):
        if self.state.screening.verdict == "reject":
            return "screening_rejected"
        return "source"  # pass and flag both get sourced — reviewers see the full picture

    @listen("screening_rejected")
    def write_rejection(self):
        s = self.state.screening
        self.state.rejection_md = self._clean_md(LLM(model=MODEL).call(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Write a short internal rejection note in markdown for "
                        f"purchase request {self._pr_number()}. State what was "
                        "requested, why it was rejected (cite the specific "
                        "policy violations), and what the requester can do "
                        "instead if there is a legitimate path. Factual, "
                        "courteous, no legalese.\n\n"
                        f"Request:\n{json.dumps(self.state.request, indent=2)}\n\n"
                        f"Screening result:\n{s.model_dump_json(indent=2)}"
                    ),
                }
            ]
        ))
        self._add_alerts()
        self.state.final_status = "rejected"
        return self._envelope()

    @listen("source")
    def run_sourcing(self):
        item_ids = {
            li["catalog_item_id"] for li in self.state.request.get("line_items", [])
        }
        offers = [
            o for o in self.state.supplier_offers if o["catalog_item_id"] in item_ids
        ]
        supplier_ids = {o["supplier_id"] for o in offers}
        suppliers = [s for s in self.state.suppliers if s["id"] in supplier_ids]

        result = (
            SourcingCrew()
            .crew()
            .kickoff(
                inputs={
                    "pr_number": self._pr_number(),
                    "request_json": json.dumps(self.state.request, indent=2),
                    "offers_json": json.dumps(offers, indent=2),
                    "suppliers_json": json.dumps(suppliers, indent=2),
                    "policy": self.state.policy_md,
                    "urgency": self.state.request.get("urgency", "normal"),
                }
            )
        )
        self.state.sourcing = result.pydantic

    @router(run_sourcing)
    def approval_gate(self):
        flagged = self.state.screening.verdict == "flag"
        over_limit = (
            self.state.sourcing.total_cost_usd > self.state.auto_approve_limit_usd
        )
        if flagged or over_limit:
            return "escalate"
        return "approve"

    @listen("escalate")
    @human_feedback(
        message=(
            "A purchase request exceeds auto-approval and needs your decision. "
            "Review the escalation memo below and reply 'approved' or "
            "'rejected' — any comments you add will be recorded."
        ),
        emit=["approved", "rejected"],
        llm=MODEL,
    )
    def request_approval(self):
        """Pauses here on AMP until the Procurement Manager responds
        (email / dashboard / webhook — SLA tracked by AMP HITL management).
        The returned memo is the content the reviewer sees."""
        reasons = []
        if self.state.screening.verdict == "flag":
            reasons.append("the screening crew flagged it for human review")
        if self.state.sourcing.total_cost_usd > self.state.auto_approve_limit_usd:
            reasons.append(
                "the sourcing total exceeds the auto-approval limit of "
                f"USD {self.state.auto_approve_limit_usd:,.0f}"
            )
        self.state.escalation_md = self._clean_md(LLM(model=MODEL).call(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Write a concise approval-request memo in markdown, "
                        "addressed to the Procurement Manager, for purchase "
                        f"request {self._pr_number()}. It needs human review "
                        f"because {' and '.join(reasons)}. Summarize the "
                        "purchase, the screening findings (violations and "
                        "anomalies, if any), the recommended supplier and "
                        "rationale, the residual risks, and end with a clear "
                        "approve/reject ask.\n\n"
                        f"Request:\n{json.dumps(self.state.request, indent=2)}\n\n"
                        f"Screening:\n{self.state.screening.model_dump_json(indent=2)}\n\n"
                        f"Sourcing:\n{self.state.sourcing.model_dump_json(indent=2)}"
                    ),
                }
            ]
        ))
        self._add_alerts()
        self.state.final_status = "needs_review"
        return self.state.escalation_md

    @listen(or_("approve", "approved"))
    def write_po(self):
        """Auto-approved under the limit, or human-approved via HITL."""
        self.state.po_md = self._generate_po()
        self.state.final_status = "approved"
        return self._envelope()

    @listen("rejected")
    def hitl_rejected(self):
        """The Procurement Manager rejected the escalated request."""
        fb = self.last_human_feedback.feedback if self.last_human_feedback else ""
        self.state.rejection_md = self._clean_md(LLM(model=MODEL).call(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Write a short internal rejection note in markdown for "
                        f"purchase request {self._pr_number()}. It was escalated "
                        "for human review and the Procurement Manager rejected "
                        f"it. Reviewer comments: {fb or '(none)'}\n\n"
                        "State what was requested, why it was escalated, and "
                        "the reviewer's decision. Factual, courteous.\n\n"
                        f"Request:\n{json.dumps(self.state.request, indent=2)}\n\n"
                        f"Screening:\n{self.state.screening.model_dump_json(indent=2)}\n\n"
                        f"Sourcing:\n{self.state.sourcing.model_dump_json(indent=2)}"
                    ),
                }
            ]
        ))
        self.state.final_status = "rejected"
        return self._envelope()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pr_number(self) -> str:
        return self.state.request.get("pr_number", "PR-DRAFT")

    @staticmethod
    def _clean_md(text: str) -> str:
        """LLMs sometimes wrap whole documents in ``` fences; strip them."""
        t = text.strip()
        if t.startswith("```"):
            t = t.split("\n", 1)[1] if "\n" in t else ""
            if t.rstrip().endswith("```"):
                t = t.rstrip()[:-3]
        return t.strip()

    def _generate_po(self) -> str:
        sourcing = self.state.sourcing
        item_ids = {
            li["catalog_item_id"] for li in self.state.request.get("line_items", [])
        }
        winning_offers = [
            o
            for o in self.state.supplier_offers
            if o["catalog_item_id"] in item_ids
            and o["supplier_name"] == (sourcing.recommended_supplier if sourcing else "")
        ]
        po = LLM(model=MODEL).call(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Draft a formal purchase order in markdown, ready for "
                        "internal review. Use PO number "
                        f"{self._pr_number().replace('PR', 'PO')}. Include "
                        "supplier details, a line items table with quantities "
                        "and prices from the winning offers, delivery and "
                        "payment terms, warranty, and special conditions. "
                        "One page.\n\n"
                        f"Purchase request:\n{json.dumps(self.state.request, indent=2)}\n\n"
                        + (
                            f"Award decision:\n{sourcing.model_dump_json(indent=2)}\n\n"
                            if sourcing
                            else ""
                        )
                        + f"Winning supplier offers:\n{json.dumps(winning_offers, indent=2)}"
                    ),
                }
            ]
        )
        return self._clean_md(po)

    def _add_alerts(self):
        s = self.state.screening
        if s is None:
            return
        severity = "high" if s.verdict == "reject" else "medium"
        for v in s.violations:
            self.state.alerts.append({"severity": severity, "message": v})
        for a in s.anomalies:
            self.state.alerts.append({"severity": severity, "message": a})

    def _envelope(self) -> dict:
        """Result returned to the caller (AMP flow_finished / status result).
        Bundled reference data is excluded — the frontend already has it."""
        return self.state.model_dump(exclude=HEAVY_INPUT_FIELDS)


def kickoff():
    """Sanity run for `crewai run`; AMP passes real inputs via the API."""
    ProcurementFlow().kickoff(
        inputs={
            "mode": "intake",
            "message": "Necesito 5 notebooks para los nuevos analistas.",
            "employee": {
                "id": "E-002",
                "name": "Matías Fernández",
                "role": "IT Support Lead",
                "approval_limit_usd": 25000,
            },
        }
    )


def plot():
    ProcurementFlow().plot()


def run_with_trigger():
    """Run the flow with a JSON trigger payload as kickoff inputs."""
    import sys

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    return ProcurementFlow().kickoff(inputs=trigger_payload)


if __name__ == "__main__":
    kickoff()
