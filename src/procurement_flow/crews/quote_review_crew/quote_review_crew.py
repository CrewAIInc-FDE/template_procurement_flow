from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.hooks import before_tool_call, unregister_before_tool_call_hook
from crewai.project import CrewBase, after_kickoff, agent, crew, task
from crewai.tools import BaseTool

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
        )
        self._quote_task_id = str(quote_task.id)
        return quote_task

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

    @after_kickoff
    def unregister_tool_hooks(self, result):
        for hook_type, hook in self._registered_hook_functions:
            if hook_type == "before_tool_call":
                unregister_before_tool_call_hook(hook)
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
