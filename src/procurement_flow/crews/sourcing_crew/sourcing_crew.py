from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from procurement_flow.types import SourcingRecommendation


@CrewBase
class SourcingCrew:
    """Compares supplier offers and produces an award recommendation."""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def cost_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["cost_analyst"],  # type: ignore[index]
        )

    @agent
    def supplier_risk_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["supplier_risk_analyst"],  # type: ignore[index]
        )

    @agent
    def procurement_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["procurement_manager"],  # type: ignore[index]
        )

    @task
    def cost_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config["cost_analysis_task"],  # type: ignore[index]
        )

    @task
    def risk_assessment_task(self) -> Task:
        return Task(
            config=self.tasks_config["risk_assessment_task"],  # type: ignore[index]
        )

    @task
    def recommendation_task(self) -> Task:
        return Task(
            config=self.tasks_config["recommendation_task"],  # type: ignore[index]
            context=[self.cost_analysis_task(), self.risk_assessment_task()],
            output_pydantic=SourcingRecommendation,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Sourcing Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
