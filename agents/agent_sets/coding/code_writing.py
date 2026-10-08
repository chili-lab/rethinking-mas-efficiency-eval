"""
Coding task agent (role-based, no tools).

Default prompt set: "coding"  (HumanEval, LCB, MBPP roles)
Can be combined with any prompt set via agents.json "prompt_set" field.

Roles (from prompt_sets/coding.py):
  Smart Programmer, Python Programmer (default), Normal Programmer,
  Stupid Programmer, Advisor Programmer, Code Reviewer, Finalizer

Usage in agents.json:
  { "agent_type": "code_writing", "role": "Smart Programmer" }
  { "agent_type": "code_writing", "prompt_set": "coding", "role": "Finalizer" }
"""
from typing import Any

from autogen_agentchat.agents import AssistantAgent

from agents.prompt_sets import get_role_description, resolve_prompt_set

_AGENT_TYPE = "code_writing"


def build_agent(name: str, model_client: Any, config: dict | None = None) -> AssistantAgent:
    prompt_set = resolve_prompt_set(_AGENT_TYPE, config)
    role = (config or {}).get("role")
    system_message = get_role_description(prompt_set, role)
    return AssistantAgent(
        name=name,
        model_client=model_client,
        system_message=system_message,
    )
