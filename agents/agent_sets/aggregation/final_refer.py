"""
Decision agent: aggregates outputs from multiple solver/analyzer agents and picks or generates the final answer.
Aligned with efficient_mas_baselines FinalRefer / "top decision-maker".
"""
from typing import Any

from autogen_agentchat.agents import AssistantAgent

# Aligned with gsm8k/mmlu get_decision_role + get_decision_constraint
SYSTEM_MESSAGE = (
    "You are the top decision-maker. "
    "You will be given a question and the answers or analyses from other agents. "
    "Please find the most reliable answer based on the analysis and results of other agents. "
    "Give reasons for making decisions. "
    "The last line of your output contains only the final result without any units, for example: The answer is 140"
)


def build_agent(name: str, model_client: Any, config: dict | None = None) -> AssistantAgent:
    return AssistantAgent(
        name=name,
        model_client=model_client,
        system_message=SYSTEM_MESSAGE,
    )
