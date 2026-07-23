import ast
import json

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.hooks import (
    after_tool_call,
    before_tool_call,
    unregister_after_tool_call_hook,
    unregister_before_tool_call_hook,
)
from crewai.project import CrewBase, after_kickoff, agent, crew, task
from crewai.tasks.task_output import TaskOutput
from crewai.tools import BaseTool

from procurement_flow.tools.gmail_tools import find_message_ref
from procurement_flow.types import QuoteCollection

_DASHES = str.maketrans({char: "-" for char in "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"})


@CrewBase
class QuoteReviewCrew:
    """Collects verifiable quote facts from recorded Gmail RFQs."""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(
        self,
        *,
        gmail_tools: list[BaseTool],
        searches: list[dict],
        model: str = "gpt-4o",
    ):
        self.gmail_tools = gmail_tools
        self.searches = searches
        self.model = model
        self._quote_task_id = ""
        self._pdf_message_ids: set[str] = set()
        self._pdf_reads: dict[str, bool] = {}

    @agent
    def quote_inbox_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["quote_inbox_analyst"],  # type: ignore[index]
            llm=self.model,
            allow_delegation=False,
        )

    @task
    def quote_extraction_task(self) -> Task:
        quote_task = Task(
            config=self.tasks_config["quote_extraction_task"],  # type: ignore[index]
            tools=self.gmail_tools,
            output_pydantic=QuoteCollection,
            guardrail=self.require_pdf_quote_details,
            guardrail_max_retries=2,
        )
        self._quote_task_id = str(quote_task.id)
        return quote_task

    def require_pdf_quote_details(self, output: TaskOutput) -> tuple[bool, str]:
        collection = output.pydantic or QuoteCollection.model_validate_json(output.raw)
        missing_reads = sorted(self._pdf_message_ids - self._pdf_reads.keys())
        if missing_reads:
            return False, (
                "PDF attachments were found but not read. Call "
                "read_gmail_pdf_attachment for these Gmail message IDs before "
                f"returning: {', '.join(missing_reads)}."
            )
        unreadable = {
            message_id
            for message_id, successful in self._pdf_reads.items()
            if not successful
        }
        invalid_quotes = [
            quote.quote_id
            for quote in collection.quotes
            if quote.message_id in unreadable
        ]
        if invalid_quotes:
            return False, (
                "The PDF reader returned a warning, so omit quote lines from those "
                "attachments and preserve the warning instead: "
                f"{', '.join(invalid_quotes)}."
            )
        return True, collection.model_dump_json()

    @before_tool_call
    def canonicalize_gmail_search(self, context) -> bool | None:
        task = getattr(context, "task", None)
        tool_name = str(getattr(context, "tool_name", "")).upper().replace(" ", "_")
        if (
            not task
            or str(getattr(task, "id", "")) != self._quote_task_id
            or "GMAIL" not in tool_name
            or "FETCH_EMAILS" not in tool_name
        ):
            return None

        serialized = str(context.tool_input).translate(_DASHES).casefold()
        matches = [
            search
            for search in self.searches
            if str(search["supplier_id"]).casefold() in serialized
        ]
        if len(matches) != 1:
            return False

        page_token = context.tool_input.get("page_token", "")
        context.tool_input.clear()
        context.tool_input.update(
            {
                "user_id": "me",
                "query": matches[0]["query"],
                "max_results": 100,
                "include_spam_trash": False,
                "include_payload": False,
            }
        )
        if page_token:
            context.tool_input["page_token"] = page_token
        return None

    @after_tool_call
    def capture_pdf_tool_state(self, context) -> None:
        tool_name = str(getattr(context, "tool_name", "")).upper().replace(" ", "_")
        raw_result = getattr(context, "raw_tool_result", context.tool_result)
        message_id = str(context.tool_input.get("message_id", ""))

        if "GMAIL" in tool_name and "FETCH" in tool_name:
            serialized = str(raw_result).casefold()
            if ".pdf" not in serialized and "application/pdf" not in serialized:
                return
            if not message_id:
                payload = raw_result
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except json.JSONDecodeError:
                        try:
                            payload = ast.literal_eval(payload)
                        except (SyntaxError, ValueError):
                            return
                message_id = find_message_ref(payload)[0]
            if message_id:
                self._pdf_message_ids.add(message_id)
            return

        if "READ_GMAIL_PDF_ATTACHMENT" in tool_name and message_id:
            result = str(raw_result).strip()
            self._pdf_reads[message_id] = bool(
                result and not result.upper().startswith("WARNING:")
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
        return Crew(
            name="Quote Review Crew",
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            cache=False,
            verbose=True,
        )
