"""
Math / arithmetic reasoning agent.

Default prompt set: "math"  (GSM8K, SVAMP, AQuA, MultiArith roles)
Can be combined with any prompt set via agents.json "prompt_set" field.

Roles (from prompt_sets/math.py):
  Math Solver, Mathematical Analyst, Programming Expert, Inspector

Usage in agents.json:
  { "agent_type": "math_solver", "role": "Math Solver" }
  { "agent_type": "math_solver", "prompt_set": "math", "role": "Inspector" }
"""
from typing import Any

from autogen_agentchat.agents import AssistantAgent

from agents.prompt_sets import get_role_description, resolve_prompt_set

_AGENT_TYPE = "math_solver"


def build_agent(name: str, model_client: Any, config: dict | None = None) -> AssistantAgent:
    prompt_set = resolve_prompt_set(_AGENT_TYPE, config)
    role = (config or {}).get("role")
    system_message = get_role_description(prompt_set, role)
    return AssistantAgent(
        name=name,
        model_client=model_client,
        system_message=system_message,
    )
