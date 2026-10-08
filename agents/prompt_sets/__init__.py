"""
Prompt set registry.

A prompt set is a collection of named role descriptions for a specific task domain.
Agent types (code_writing, math_solver, analyze_agent, …) are decoupled from prompt sets:
any agent type can be combined with any prompt set that contains the required roles.

Usage in agents.json:
    { "agent_type": "code_writing", "prompt_set": "coding", "role": "Smart Programmer" }
    { "agent_type": "math_solver",  "prompt_set": "math",   "role": "Inspector" }
    { "agent_type": "code_writing", "prompt_set": "coding", "role": "Finalizer" }

If "prompt_set" is omitted, the agent type falls back to its own DEFAULT_PROMPT_SET.
"""
import importlib
from typing import Any

# Maps prompt_set name → module path inside agents/prompt_sets/
SUPPORTED_PROMPT_SETS: dict[str, str] = {
    "coding":   "agents.prompt_sets.coding",
    "math":     "agents.prompt_sets.math",
    "analysis": "agents.prompt_sets.analysis",
}

# Default prompt set per agent type (used when agents.json omits "prompt_set")
AGENT_DEFAULT_PROMPT_SET: dict[str, str] = {
    "code_writing":  "coding",
    "math_solver":   "math",
    "analyze_agent": "analysis",
}


def _load_module(prompt_set: str):
    try:
        module_path = SUPPORTED_PROMPT_SETS[prompt_set]
    except KeyError:
        raise ValueError(
            f"Prompt set '{prompt_set}' not found. "
            f"Available: {list(SUPPORTED_PROMPT_SETS.keys())}"
        )
    return importlib.import_module(module_path)


def get_role_description(prompt_set: str, role: str | None) -> str:
    """
    Return the system message for *role* from *prompt_set*.
    Falls back to the prompt set's DEFAULT_ROLE if *role* is None or not found.
    """
    mod = _load_module(prompt_set)
    role_map: dict[str, str] = mod.ROLE_DESCRIPTION
    default_role: str = mod.DEFAULT_ROLE

    resolved_role = role if (role and role in role_map) else default_role
    return role_map[resolved_role]


def get_default_role(prompt_set: str) -> str:
    """Return the default role name for a given prompt set."""
    return _load_module(prompt_set).DEFAULT_ROLE


def list_roles(prompt_set: str) -> list[str]:
    """Return all available role names for a given prompt set."""
    return list(_load_module(prompt_set).ROLE_DESCRIPTION.keys())


def resolve_role(prompt_set: str, role: str | None) -> str:
    """Return the effective role name, falling back to the prompt set's DEFAULT_ROLE."""
    mod = _load_module(prompt_set)
    role_map: dict[str, str] = mod.ROLE_DESCRIPTION
    default_role: str = mod.DEFAULT_ROLE
    return role if (role and role in role_map) else default_role


def resolve_prompt_set(agent_type: str, config: dict[str, Any] | None) -> str:
    """
    Determine the effective prompt set for an agent, checking (in order):
      1. config["prompt_set"]  (explicit override in agents.json)
      2. AGENT_DEFAULT_PROMPT_SET[agent_type]  (per-type default)
      3. raise ValueError if neither is available
    """
    cfg = config or {}
    if "prompt_set" in cfg:
        return cfg["prompt_set"]
    if agent_type in AGENT_DEFAULT_PROMPT_SET:
        return AGENT_DEFAULT_PROMPT_SET[agent_type]
    raise ValueError(
        f"No default prompt set for agent type '{agent_type}'. "
        f"Specify 'prompt_set' explicitly in agents.json."
    )
