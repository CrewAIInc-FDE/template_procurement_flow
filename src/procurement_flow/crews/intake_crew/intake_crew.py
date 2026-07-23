import ast
import json
from datetime import datetime, timezone
from email.utils import parseaddr
from typing import Any

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.hooks import (
    after_tool_call,
    before_tool_call,
    unregister_after_tool_call_hook,
    unregister_before_tool_call_hook,
)
from crewai.project import CrewBase, after_kickoff, agent, crew, task
from crewai.tasks.conditional_task import ConditionalTask
from crewai.tasks.task_output import TaskOutput
from crewai.tools import BaseTool

from procurement_flow.tools.gmail_tools import (
    GMAIL_FETCH_EMAILS,
    GMAIL_SEND_EMAIL,
    find_message_ref,
)
from procurement_flow.types import (
    RfqDispatch,
    RfqDispatchBatch,
    ScreeningResult,
    SourcingPlan,
    SupplierShortlist,
)


def _email_address(value: str) -> str:
    value = (value or "").strip()
    parsed = parseaddr(value)[1]
    if parsed != value or parsed.count("@") != 1 or any(c.isspace() for c in parsed):
        return ""
    local, domain = parsed.rsplit("@", 1)
    return parsed if local and "." in domain else ""


def _action(tool_name: str) -> str:
    name = tool_name.upper()
    if "GMAIL" in name and "FETCH_EMAILS" in name:
        return GMAIL_FETCH_EMAILS
    if "GMAIL" in name and "SEND_EMAIL" in name:
        return GMAIL_SEND_EMAIL
    return ""


def _payload(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return None


def _payload_error(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    if value.get("successful") is False:
        return str(value.get("error") or "Gmail tool call failed")
    return str(value.get("error") or "") if value.get("error") else ""


@CrewBase
class ProcurementIntakeCrew:
    """Extracts, screens, shortlists, and conditionally dispatches one request."""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(
        self,
        *,
        pr_number: str,
        catalog: list[dict],
        suppliers: list[dict],
        gmail_tools: list[BaseTool] | None = None,
        dispatch_error: str = "",
        override_recipient: str = "",
        model: str = "gpt-4o",
    ):
        self.pr_number = pr_number
        self.catalog = catalog
        self.suppliers = suppliers
        self.gmail_tools = gmail_tools or []
        self.dispatch_error = dispatch_error
        self.override_recipient = override_recipient
        self.model = model
        self.validated_plan: SourcingPlan | None = None
        self.dispatch_batch = RfqDispatchBatch()
        self._dispatch_specs: dict[str, dict] = {}
        self._tool_results: dict[str, dict] = {}
        self._runtime_crew: Crew | None = None

    @agent
    def sourcing_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["sourcing_agent"],  # type: ignore[index]
            llm=self.model,
            allow_delegation=False,
        )

    @agent
    def policy_compliance_officer(self) -> Agent:
        return Agent(
            config=self.agents_config["policy_compliance_officer"],  # type: ignore[index]
            llm=self.model,
            allow_delegation=False,
        )

    @agent
    def fraud_anomaly_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["fraud_anomaly_analyst"],  # type: ignore[index]
            llm=self.model,
            allow_delegation=False,
        )

    def validate_sourcing_plan(self, output: TaskOutput) -> tuple[bool, Any]:
        try:
            plan = output.pydantic or SourcingPlan.model_validate_json(output.raw)
            if not isinstance(plan, SourcingPlan):
                plan = SourcingPlan.model_validate(plan)

            catalog_by_id = {str(item["id"]): item for item in self.catalog}
            request_items = []
            unmatched = list(plan.request_draft.unmatched)
            for line in plan.request_draft.line_items:
                item = catalog_by_id.get(line.catalog_item_id)
                if item is None:
                    unmatched.append(line.name or line.catalog_item_id)
                    continue
                if line.quantity < 1:
                    return False, f"Quantity for {line.catalog_item_id} must be positive."
                request_items.append(
                    line.model_copy(
                        update={
                            "sku": item["sku"],
                            "name": item["name"],
                            "unit_price_usd": item["unit_price_usd"],
                            "line_total_usd": round(
                                line.quantity * item["unit_price_usd"], 2
                            ),
                        }
                    )
                )

            draft = plan.request_draft.model_copy(
                update={
                    "line_items": request_items,
                    "unmatched": list(dict.fromkeys(unmatched)),
                    "estimated_total_usd": round(
                        sum(item.line_total_usd for item in request_items), 2
                    ),
                }
            )
            requested = {item.catalog_item_id: item for item in request_items}
            suppliers_by_id = {
                str(supplier["id"]): supplier for supplier in self.suppliers
            }
            shortlisted: dict[str, list[str]] = {}
            for candidate in plan.supplier_shortlist:
                supplier = suppliers_by_id.get(candidate.supplier_id)
                if supplier is None:
                    return False, f"Unknown supplier {candidate.supplier_id}."
                categories = set(supplier.get("categories") or [])
                for item_id in dict.fromkeys(candidate.catalog_item_ids):
                    if item_id not in requested:
                        return False, f"Supplier {candidate.supplier_id} references unrequested item {item_id}."
                    category = catalog_by_id[item_id].get("category")
                    if category not in categories:
                        return False, (
                            f"Supplier {candidate.supplier_id} is incompatible with "
                            f"{item_id} category {category}."
                        )
                    shortlisted.setdefault(candidate.supplier_id, [])
                    if item_id not in shortlisted[candidate.supplier_id]:
                        shortlisted[candidate.supplier_id].append(item_id)

            self.validated_plan = SourcingPlan(
                request_draft=draft,
                supplier_shortlist=[
                    SupplierShortlist(
                        supplier_id=supplier_id,
                        catalog_item_ids=item_ids,
                    )
                    for supplier_id, item_ids in shortlisted.items()
                ],
            )
            self._build_dispatch_specs()
            return True, self.validated_plan.model_dump_json()
        except (KeyError, TypeError, ValueError) as exc:
            return False, f"Invalid sourcing plan: {exc}"

    def _build_dispatch_specs(self) -> None:
        self._dispatch_specs = {}
        if self.validated_plan is None:
            return
        suppliers_by_id = {
            str(supplier["id"]): supplier for supplier in self.suppliers
        }
        lines_by_id = {
            line.catalog_item_id: line
            for line in self.validated_plan.request_draft.line_items
        }
        override_raw = self.override_recipient.strip()
        override = _email_address(override_raw)

        for candidate in self.validated_plan.supplier_shortlist:
            supplier = suppliers_by_id[candidate.supplier_id]
            intended = _email_address(str(supplier.get("email") or ""))
            actual = override or intended
            dispatch = RfqDispatch(
                rfq_id=f"RFQ-{self.pr_number}-{candidate.supplier_id}",
                supplier_id=candidate.supplier_id,
                supplier_name=str(supplier.get("name") or candidate.supplier_id),
                intended_recipient=intended,
                actual_recipient=actual,
                override_applied=bool(override),
                status="failed",
            )
            error = ""
            if override_raw and not override:
                error = "the demo recipient override is invalid"
            elif not actual:
                error = "no valid supplier recipient is configured"
            elif not override and actual.rsplit("@", 1)[1].endswith(".example"):
                error = "placeholder supplier emails require the demo override"
            elif self.dispatch_error:
                error = self.dispatch_error

            lines = [lines_by_id[item_id] for item_id in candidate.catalog_item_ids]
            items = "\n".join(
                f"- {line.sku} — {line.name}: quantity {line.quantity}"
                for line in lines
            )
            demo_note = (
                f"\nDemo routing: please respond as {dispatch.supplier_name}.\n"
                if dispatch.override_applied
                else "\n"
            )
            subject = (
                f"[{dispatch.rfq_id}] Quote request for {self.pr_number} "
                f"— {dispatch.supplier_name}"
            )
            body = (
                f"Hello {dispatch.supplier_name},\n\n"
                f"Please provide a quote for purchase request {self.pr_number}.\n"
                f"Reference: {dispatch.rfq_id}\n\n"
                f"Requested items:\n{items}\n"
                f"{demo_note}\n"
                "Reply to this email without changing the subject. For each item, include "
                "the unit price, currency (USD or CLP), and delivery time in days. You may "
                "include the quote in the email body or attach a text-based PDF.\n\n"
                "Thank you."
            )
            self._dispatch_specs[dispatch.rfq_id] = {
                "dispatch": dispatch,
                "error": error,
                "query": f'in:sent to:{actual} "{dispatch.rfq_id}"',
                "subject": subject,
                "body": body,
            }

    def _matching_spec(self, tool_input: dict) -> tuple[str, dict] | None:
        serialized = json.dumps(tool_input, ensure_ascii=False)
        matches = [
            (rfq_id, spec)
            for rfq_id, spec in self._dispatch_specs.items()
            if rfq_id in serialized
        ]
        return matches[0] if len(matches) == 1 else None

    @before_tool_call
    def guard_gmail_tool(self, context) -> bool | None:
        if getattr(context, "crew", None) is not self._runtime_crew:
            return None
        action = _action(context.tool_name)
        if not action:
            return None
        match = self._matching_spec(context.tool_input)
        if match is None:
            return False
        rfq_id, spec = match
        if spec["error"]:
            return False

        state = self._tool_results.setdefault(rfq_id, {})
        if action == GMAIL_FETCH_EMAILS:
            context.tool_input.clear()
            context.tool_input.update(
                {
                    "user_id": "me",
                    "query": spec["query"],
                    "max_results": 10,
                    "include_spam_trash": False,
                    "include_payload": False,
                }
            )
            return None

        if (
            not state.get("search_complete")
            or state.get("error")
            or state.get("existing_message_id")
            or state.get("sent_message_id")
        ):
            return False
        state["send_attempted"] = True
        context.tool_input.clear()
        context.tool_input.update(
            {
                "user_id": "me",
                "recipient_email": spec["dispatch"].actual_recipient,
                "subject": spec["subject"],
                "body": spec["body"],
            }
        )
        return None

    @after_tool_call
    def capture_gmail_result(self, context) -> str | None:
        if getattr(context, "crew", None) is not self._runtime_crew:
            return None
        action = _action(context.tool_name)
        match = self._matching_spec(context.tool_input)
        if not action or match is None:
            return None
        rfq_id, _ = match
        state = self._tool_results.setdefault(rfq_id, {})
        raw_result = getattr(context, "raw_tool_result", context.tool_result)
        if isinstance(raw_result, str) and raw_result.startswith(
            "Tool execution blocked by hook"
        ):
            return None
        payload = _payload(raw_result)
        error = _payload_error(payload)
        if payload is None:
            error = "Gmail tool returned an unreadable response"

        message_id, thread_id = find_message_ref(payload)
        if action == GMAIL_FETCH_EMAILS:
            state["search_complete"] = not error
            if error:
                state["error"] = error
            elif message_id:
                state["existing_message_id"] = message_id
                state["existing_thread_id"] = thread_id
        elif error:
            state["error"] = error
        elif message_id:
            state["sent_message_id"] = message_id
            state["sent_thread_id"] = thread_id
        else:
            state["error"] = "Gmail send did not return a verifiable message ID"
        return None

    def validate_dispatch_batch(self, _: TaskOutput) -> tuple[bool, Any]:
        warnings = []
        dispatches = []
        sent_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for rfq_id, spec in self._dispatch_specs.items():
            state = self._tool_results.get(rfq_id, {})
            dispatch = spec["dispatch"].model_copy(deep=True)
            message_id = state.get("existing_message_id") or state.get("sent_message_id")
            thread_id = state.get("existing_thread_id") or state.get("sent_thread_id") or ""
            if message_id:
                dispatch.gmail_message_id = message_id
                dispatch.gmail_thread_id = thread_id
                dispatch.status = "sent"
                dispatch.sent_at = sent_at
            else:
                dispatch.error = (
                    spec["error"]
                    or state.get("error")
                    or (
                        "Gmail Sent search did not complete; RFQ was not sent"
                        if not state.get("search_complete")
                        else "RFQ dispatch did not return a verifiable message ID"
                    )
                )
                warnings.append(
                    f"RFQ to {dispatch.supplier_name} was not sent: {dispatch.error}"
                )
            dispatches.append(dispatch)
        if not dispatches:
            warnings.append("No approved supplier covers the requested catalog items.")
        self.dispatch_batch = RfqDispatchBatch(
            dispatches=dispatches,
            warnings=warnings,
        )
        return True, self.dispatch_batch.model_dump_json()

    @staticmethod
    def should_dispatch(output: TaskOutput) -> bool:
        verdict = output.pydantic or ScreeningResult.model_validate_json(output.raw)
        return verdict.verdict in {"pass", "flag"}

    @task
    def sourcing_plan_task(self) -> Task:
        return Task(
            config=self.tasks_config["sourcing_plan_task"],  # type: ignore[index]
            output_pydantic=SourcingPlan,
            guardrail=self.validate_sourcing_plan,
        )

    @task
    def compliance_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["compliance_check_task"],  # type: ignore[index]
            context=[self.sourcing_plan_task()],
        )

    @task
    def anomaly_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["anomaly_check_task"],  # type: ignore[index]
            context=[self.sourcing_plan_task()],
        )

    @task
    def screening_verdict_task(self) -> Task:
        return Task(
            config=self.tasks_config["screening_verdict_task"],  # type: ignore[index]
            context=[self.compliance_check_task(), self.anomaly_check_task()],
            output_pydantic=ScreeningResult,
        )

    @task
    def rfq_dispatch_task(self) -> ConditionalTask:
        return ConditionalTask(
            config=self.tasks_config["rfq_dispatch_task"],  # type: ignore[index]
            condition=self.should_dispatch,
            context=[self.sourcing_plan_task(), self.screening_verdict_task()],
            tools=self.gmail_tools,
            output_pydantic=RfqDispatchBatch,
            guardrail=self.validate_dispatch_batch,
            guardrail_max_retries=0,
        )

    @after_kickoff
    def unregister_tool_hooks(self, result):
        unregister = {
            "before_tool_call": unregister_before_tool_call_hook,
            "after_tool_call": unregister_after_tool_call_hook,
        }
        for hook_type, hook in self._registered_hook_functions:
            if hook_type in unregister:
                unregister[hook_type](hook)
        self._registered_hook_functions = []
        return result

    @crew
    def crew(self) -> Crew:
        self._runtime_crew = Crew(
            name="Procurement Intake Crew",
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            cache=False,
            verbose=True,
        )
        return self._runtime_crew
