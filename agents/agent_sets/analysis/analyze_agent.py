"""
Multi-domain knowledge / QA analysis agent.

Default prompt set: "analysis"  (MMLU, ARC roles)
Can be combined with any prompt set via agents.json "prompt_set" field.

Roles (from prompt_sets/analysis.py):
  Knowlegable Expert, Wiki Searcher, Critic, Mathematician, Psychologist,
  Historian, Doctor, Lawyer, Economist, Programmer

Usage in agents.json:
  { "agent_type": "analyze_agent", "role": "Critic" }
  { "agent_type": "analyze_agent", "prompt_set": "analysis", "role": "Doctor" }
"""
from typing import Any

from autogen_agentchat.agents import AssistantAgent

from agents.prompt_sets import get_role_description, resolve_prompt_set

_AGENT_TYPE = "analyze_agent"


def build_agent(name: str, model_client: Any, config: dict | None = None) -> AssistantAgent:
    prompt_set = resolve_prompt_set(_AGENT_TYPE, config)
    role = (config or {}).get("role")
    system_message = get_role_description(prompt_set, role)
    return AssistantAgent(
        name=name,
        model_client=model_client,
        system_message=system_message,
    )
