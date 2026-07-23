from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai.tools import BaseTool

from procurement_flow.types import QuoteCollection


@CrewBase
class QuoteReviewCrew:
    """Collects verifiable quote facts from recorded Gmail RFQs."""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self, *, gmail_tools: list[BaseTool], model: str = "gpt-4o"):
        self.gmail_tools = gmail_tools
        self.model = model

    @agent
    def quote_inbox_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["quote_inbox_analyst"],  # type: ignore[index]
            llm=self.model,
            allow_delegation=False,
        )

    @task
    def quote_extraction_task(self) -> Task:
        return Task(
            config=self.tasks_config["quote_extraction_task"],  # type: ignore[index]
            tools=self.gmail_tools,
            output_pydantic=QuoteCollection,
        )

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
