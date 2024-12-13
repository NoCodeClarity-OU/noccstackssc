from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff
from .tools.custom_tool import ClarityDocScraper, SmartContractGenerator, TestGenerator

# If you want to run a snippet of code before or after the crew starts, 
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class Noccstacksv2():
	"""Noccstacksv2 crew for developing Clarity smart contracts"""

	# Add default inputs to handle missing input cases
	default_inputs = {
		"project_name": "Newsletter",
		"project_description": "A decentralized newsletter platform built on Stacks blockchain that allows users to subscribe, publish content, and manage subscriptions. Features include subscription management, content publishing, payment handling, and governance features."
	}

	# Learn more about YAML configuration files here:
	# Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
	# Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'

	# If you would like to add tools to your agents, you can learn more about it here:
	# https://docs.crewai.com/concepts/agents#agent-tools
	@agent
	def project_manager(self) -> Agent:
		return Agent(
			config=self.agents_config['project_manager'],
			verbose=True
		)

	@agent
	def smart_contract_developer(self) -> Agent:
		return Agent(
			config=self.agents_config['smart_contract_developer'],
			verbose=True,
			tools=[ClarityDocScraper(), SmartContractGenerator()]
		)

	@agent
	def testing_agent(self) -> Agent:
		return Agent(
			config=self.agents_config['testing_agent'],
			verbose=True,
			tools=[TestGenerator()]
		)

	# To learn more about structured task outputs, 
	# task dependencies, and task callbacks, check out the documentation:
	# https://docs.crewai.com/concepts/tasks#overview-of-a-task
	@task
	def analyze_project(self) -> Task:
		return Task(
			config=self.tasks_config['analyze_project']
		)

	@task
	def develop_smart_contract(self) -> Task:
		return Task(
			config=self.tasks_config['develop_smart_contract']
		)

	@task
	def create_tests(self) -> Task:
		return Task(
			config=self.tasks_config['create_tests']
		)

	@crew
	def crew(self) -> Crew:
		"""Creates the Noccstacksv2 crew for smart contract development"""
		# To learn how to add knowledge sources to your crew, check out the documentation:
		# https://docs.crewai.com/concepts/knowledge#what-is-knowledge

		# Create crew with input handling
		crew = Crew(
			agents=self.agents,
			tasks=self.tasks,
			process=Process.sequential,
			verbose=True,
		)
		
		return crew

	# Add before_kickoff decorator to handle input merging
	@before_kickoff
	def before_kickoff_function(self, inputs):
		"""Merge default inputs with provided inputs"""
		merged_inputs = self.default_inputs.copy()
		if inputs:
			merged_inputs.update(inputs)
		return merged_inputs
