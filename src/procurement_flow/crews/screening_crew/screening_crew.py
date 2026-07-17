from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from procurement_flow.types import ScreeningResult


@CrewBase
class ScreeningCrew:
    """Screens purchase requests for policy compliance and fraud signals."""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def policy_compliance_officer(self) -> Agent:
        return Agent(
            config=self.agents_config["policy_compliance_officer"],  # type: ignore[index]
        )

    @agent
    def fraud_anomaly_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["fraud_anomaly_analyst"],  # type: ignore[index]
        )

    @task
    def compliance_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["compliance_check_task"],  # type: ignore[index]
        )

    @task
    def anomaly_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["anomaly_check_task"],  # type: ignore[index]
        )

    @task
    def screening_verdict_task(self) -> Task:
        return Task(
            config=self.tasks_config["screening_verdict_task"],  # type: ignore[index]
            context=[self.compliance_check_task(), self.anomaly_check_task()],
            output_pydantic=ScreeningResult,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Screening Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
