#!/usr/bin/env python
import json
import os
from email.utils import parseaddr
from pathlib import Path

from crewai.flow import Flow, human_feedback, listen, router, start
from pydantic import BaseModel, Field

from procurement_flow.crews.intake_crew.intake_crew import ProcurementIntakeCrew
from procurement_flow.crews.quote_review_crew.quote_review_crew import QuoteReviewCrew
from procurement_flow.procurement import (
    build_quote_review,
    generate_purchase_orders,
    materialize_awards,
    parse_award_feedback,
)
from procurement_flow.tools.gmail_tools import (
    ReadGmailPdfAttachmentTool,
    gmail_dispatch_tools,
    gmail_quote_tools,
)
from procurement_flow.types import (
    AwardedItem,
    PurchaseOrderDocument,
    QuoteCollection,
    QuoteReview,
    RequestDraft,
    RfqDispatch,
    RfqDispatchBatch,
    ScreeningResult,
    SourcingPlan,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")

HEAVY_INPUT_FIELDS = {
    "catalog",
    "suppliers",
    "policy_md",
    "recent_requests",
    "existing_awards",
    "existing_purchase_orders",
}
COMPOSIO_ENV_VARS = ("COMPOSIO_API_KEY", "COMPOSIO_USER_ID")


def _missing_composio_env() -> list[str]:
    return [name for name in COMPOSIO_ENV_VARS if not os.getenv(name, "").strip()]


def gmail_reply_query(dispatch: RfqDispatch) -> str:
    return (
        f'in:inbox -from:me from:{dispatch.actual_recipient} '
        f'"{dispatch.rfq_id}"'
    )


class ProcurementState(BaseModel):
    # kickoff inputs
    mode: str = "intake"  # intake | quote_review
    message: str = ""
    employee: dict = Field(default_factory=dict)
    request: dict = Field(default_factory=dict)
    recent_requests: list = Field(default_factory=list)
    catalog: list = Field(default_factory=list)
    suppliers: list = Field(default_factory=list)
    policy_md: str = ""
    clp_per_usd: float = 0
    existing_awards: list[AwardedItem] = Field(default_factory=list)
    existing_purchase_orders: list[dict] = Field(default_factory=list)
    rfq_dispatches: list[RfqDispatch] = Field(default_factory=list)
    # outputs
    request_draft: RequestDraft | None = None
    screening: ScreeningResult | None = None
    quote_review: QuoteReview | None = None
    new_awards: list[AwardedItem] = Field(default_factory=list)
    purchase_orders: list[PurchaseOrderDocument] = Field(default_factory=list)
    final_status: str = ""  # rfq_failed | awaiting_quotes | needs_review | approved | rejected
    rejection_md: str = ""
    alerts: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProcurementFlow(Flow[ProcurementState]):
    """Two independent processes in one deployment: intake and quote review."""

    @start()
    def receive(self):
        if not self.state.catalog:
            self.state.catalog = json.loads(
                (DATA_DIR / "seed" / "catalog_items.json").read_text()
            )
        if not self.state.suppliers:
            self.state.suppliers = json.loads(
                (DATA_DIR / "seed" / "suppliers.json").read_text()
            )
        if not self.state.policy_md:
            self.state.policy_md = (DATA_DIR / "procurement_policy.md").read_text()

    @router(receive)
    def dispatch(self):
        return self.state.mode

    # ------------------------------------------------------------- intake

    @listen("intake")
    def run_intake(self):
        missing_composio_env = _missing_composio_env()
        dispatch_error = (
            f"{', '.join(missing_composio_env)} is missing"
            if missing_composio_env
            else ""
        )
        tools = []
        if not dispatch_error:
            try:
                tools = gmail_dispatch_tools()
            except RuntimeError as exc:
                dispatch_error = str(exc)

        intake = ProcurementIntakeCrew(
            pr_number=self._pr_number(),
            catalog=self.state.catalog,
            suppliers=self.state.suppliers,
            gmail_tools=tools,
            dispatch_error=dispatch_error,
            override_recipient=os.getenv("DEMO_RFQ_RECIPIENT_OVERRIDE", ""),
            model=MODEL,
        )
        crew = intake.crew()
        crew.kickoff(
            inputs={
                "pr_number": self._pr_number(),
                "message": self.state.message,
                "employee_json": json.dumps(self.state.employee, indent=2),
                "recent_requests_json": json.dumps(
                    self.state.recent_requests, indent=2
                ),
                "catalog_json": json.dumps(self.state.catalog, indent=2),
                "suppliers_json": json.dumps(self.state.suppliers, indent=2),
                "policy": self.state.policy_md,
                "demo_recipient": os.getenv(
                    "DEMO_RFQ_RECIPIENT_OVERRIDE", ""
                ).strip()
                or "(none)",
            }
        )
        outputs = {task.name: task.output for task in crew.tasks}
        sourcing_output = outputs["sourcing_plan_task"]
        plan = sourcing_output.pydantic or SourcingPlan.model_validate_json(
            sourcing_output.raw
        )
        self.state.request_draft = plan.request_draft
        self.state.request = {
            "pr_number": self._pr_number(),
            **plan.request_draft.model_dump(mode="json"),
        }
        screening_output = outputs["screening_verdict_task"]
        self.state.screening = (
            screening_output.pydantic
            or ScreeningResult.model_validate_json(screening_output.raw)
        )
        self._add_screening_alerts()
        if self.state.screening and self.state.screening.verdict == "reject":
            return self._finish_rejection(
                "The request failed the procurement screening gate."
            )

        dispatch_output = outputs["rfq_dispatch_task"]
        batch = (
            dispatch_output.pydantic
            if dispatch_output and dispatch_output.pydantic
            else intake.dispatch_batch
        )
        if not isinstance(batch, RfqDispatchBatch):
            batch = RfqDispatchBatch.model_validate(batch)
        self.state.rfq_dispatches = batch.dispatches
        self.state.warnings.extend(batch.warnings)
        sent = sum(d.status in {"sent", "replied"} for d in self.state.rfq_dispatches)
        self.state.final_status = "awaiting_quotes" if sent else "rfq_failed"
        self._add_warning_alerts()
        return self._envelope()

    # -------------------------------------------------------- quote review

    @listen("quote_review")
    def run_quote_collection(self):
        if self.state.clp_per_usd <= 0:
            self.state.warnings.append("CLP per USD must be configured before quote review.")
            self.state.final_status = "awaiting_quotes"
            return
        missing_composio_env = _missing_composio_env()
        if missing_composio_env:
            self.state.warnings.append(
                "Composio Gmail is not configured: "
                f"{', '.join(missing_composio_env)} is missing."
            )
            self.state.final_status = "awaiting_quotes"
            return
        if not any(d.status in {"sent", "replied"} for d in self.state.rfq_dispatches):
            self.state.warnings.append("No sent RFQ threads are recorded for this request.")
            self.state.final_status = "awaiting_quotes"
            return
        try:
            collection = self._collect_gmail_quotes()
            self._apply_reply_metadata(collection)
            self.state.quote_review = build_quote_review(
                pr_number=self._pr_number(),
                request_items=self.state.request.get("line_items", []),
                quotes=collection.quotes,
                clp_per_usd=self.state.clp_per_usd,
                suppliers=self.state.suppliers,
                warnings=collection.warnings,
            )
            self.state.warnings = self.state.quote_review.warnings
        except Exception as exc:
            self.state.warnings.append(f"Gmail quote review failed: {exc}")
            self.state.final_status = "awaiting_quotes"

    @router(run_quote_collection)
    def quote_gate(self):
        if self.state.quote_review and self.state.quote_review.lines:
            return "review_quotes"
        return "no_quotes"

    @listen("no_quotes")
    def finish_no_quotes(self):
        if not self.state.warnings:
            self.state.warnings.append(
                f'No complete quotes were found in the inbox for {self._pr_number()}.'
            )
        self._add_warning_alerts()
        self.state.final_status = "awaiting_quotes"
        return self._envelope()

    @listen("review_quotes")
    @human_feedback(
        message=(
            "Review the proposed per-item supplier awards. Reply approved to use the "
            "suggestions, rejected to close the request, or submit the portal's award JSON."
        ),
        emit=["approved", "rejected"],
        llm=MODEL,
        default_outcome="rejected",
    )
    def request_award_approval(self):
        self.state.final_status = "needs_review"
        self._add_warning_alerts()
        return self.state.quote_review.model_dump(mode="json")

    @listen("approved")
    def apply_approval(self, result):
        feedback = getattr(result, "feedback", "approved") or "approved"
        try:
            decision, selections = parse_award_feedback(
                feedback, self.state.quote_review
            )
            if decision == "rejected":
                return self._finish_rejection("The procurement analyst rejected the proposal.")
            self.state.new_awards = materialize_awards(
                self.state.quote_review, selections
            )
            self.state.purchase_orders = generate_purchase_orders(
                pr_number=self._pr_number(),
                existing_awards=self.state.existing_awards,
                new_awards=self.state.new_awards,
                existing_purchase_orders=self.state.existing_purchase_orders,
                clp_per_usd=self.state.clp_per_usd,
            )
            self.state.final_status = (
                "awaiting_quotes"
                if self.state.quote_review.uncovered_item_ids
                else "approved"
            )
        except ValueError as exc:
            self.state.warnings.append(f"Award approval was not applied: {exc}")
            self._add_warning_alerts()
            self.state.final_status = "awaiting_quotes"
        return self._envelope()

    @listen("rejected")
    def apply_rejection(self, result):
        feedback = getattr(result, "feedback", "") or ""
        return self._finish_rejection(
            f"The procurement analyst rejected the proposal. Reviewer feedback: {feedback or '(none)'}"
        )

    # -------------------------------------------------------------- helpers

    def _collect_gmail_quotes(self) -> QuoteCollection:
        pr_number = self._pr_number()
        dispatches = [
            d for d in self.state.rfq_dispatches if d.status in {"sent", "replied"}
        ]
        searches = [
            {
                **dispatch.model_dump(mode="json"),
                "query": gmail_reply_query(dispatch),
            }
            for dispatch in dispatches
        ]
        quote_review = QuoteReviewCrew(
            gmail_tools=[*gmail_quote_tools(), ReadGmailPdfAttachmentTool()],
            model=MODEL,
        )
        result = quote_review.crew().kickoff(
            inputs={
                "pr_number": pr_number,
                "searches_json": json.dumps(searches, indent=2),
                "request_items_json": json.dumps(
                    self.state.request.get("line_items", []), indent=2
                ),
                "suppliers_json": json.dumps(self.state.suppliers, indent=2),
                "policy": self.state.policy_md,
            }
        )
        collection = result.pydantic or QuoteCollection.model_validate_json(result.raw)
        return self._sanitize_quote_collection(collection)

    def _sanitize_quote_collection(self, collection: QuoteCollection) -> QuoteCollection:
        by_rfq = {
            d.rfq_id: d
            for d in self.state.rfq_dispatches
            if d.status in {"sent", "replied"}
        }
        replies = []
        for reply in collection.replies:
            dispatch = by_rfq.get(reply.rfq_id)
            if not dispatch or reply.message_id == dispatch.gmail_message_id:
                collection.warnings.append(
                    f"Ignored message {reply.message_id}: it is not an inbound recorded RFQ reply."
                )
                continue
            if "INBOX" not in reply.label_ids or (
                parseaddr(reply.sender)[1].casefold()
                != dispatch.actual_recipient.casefold()
            ):
                collection.warnings.append(
                    f"Ignored message {reply.message_id}: sender or Gmail labels do not match {reply.rfq_id}."
                )
                continue
            if dispatch.gmail_thread_id and reply.thread_id != dispatch.gmail_thread_id:
                collection.warnings.append(
                    f"Ignored message {reply.message_id}: Gmail thread does not match {reply.rfq_id}."
                )
                continue
            replies.append(reply)
        collection.replies = replies
        reply_keys = {(r.rfq_id, r.message_id): r for r in replies}

        quotes = []
        for quote in collection.quotes:
            dispatch = by_rfq.get(quote.rfq_id)
            reply = reply_keys.get((quote.rfq_id, quote.message_id))
            if not dispatch or not reply:
                collection.warnings.append(
                    f"Ignored quote {quote.quote_id}: source is not a verified RFQ reply."
                )
                continue
            quote.supplier_id = dispatch.supplier_id
            quote.supplier_name = dispatch.supplier_name
            quote.thread_id = reply.thread_id
            quotes.append(quote)
        collection.quotes = quotes
        collection.warnings = list(dict.fromkeys(collection.warnings))
        return collection

    def _apply_reply_metadata(self, collection: QuoteCollection):
        by_rfq: dict[str, list] = {}
        for reply in collection.replies:
            by_rfq.setdefault(reply.rfq_id, []).append(reply)
        for dispatch in self.state.rfq_dispatches:
            replies = by_rfq.get(dispatch.rfq_id, [])
            if not replies:
                continue
            dispatch.status = "replied"
            dispatch.reply_count = len({reply.message_id for reply in replies})
            dispatch.last_reply_at = max(reply.received_at for reply in replies)

    def _pr_number(self) -> str:
        return self.state.request.get("pr_number", "PR-DRAFT")

    def _add_screening_alerts(self):
        screening = self.state.screening
        if not screening:
            return
        severity = "high" if screening.verdict == "reject" else "medium"
        for message in [*screening.violations, *screening.anomalies]:
            self.state.alerts.append({"severity": severity, "message": message})

    def _add_warning_alerts(self):
        existing = {a["message"] for a in self.state.alerts}
        for warning in self.state.warnings:
            if warning not in existing:
                self.state.alerts.append({"severity": "medium", "message": warning})

    def _rejection_note(self, reason: str) -> str:
        screening = self.state.screening
        findings = []
        if screening:
            findings = [*screening.violations, *screening.anomalies]
        bullets = "\n".join(f"- {finding}" for finding in findings) or "- No additional findings recorded."
        return (
            f"# Purchase request {self._pr_number()} rejected\n\n"
            f"{reason}\n\n## Findings\n\n{bullets}"
        )

    def _finish_rejection(self, reason: str):
        self.state.rejection_md = self._rejection_note(reason)
        self.state.final_status = "rejected"
        return self._envelope()

    def _envelope(self) -> dict:
        return self.state.model_dump(mode="json", exclude=HEAVY_INPUT_FIELDS)


def kickoff():
    """Smoke run for `crewai run`; production passes inputs through AMP."""
    return ProcurementFlow().kickoff(
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
    import sys

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")
    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        raise Exception("Invalid JSON payload provided as argument") from exc
    return ProcurementFlow().kickoff(inputs=trigger_payload)


if __name__ == "__main__":
    kickoff()
