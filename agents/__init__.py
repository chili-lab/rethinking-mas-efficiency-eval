import importlib
from typing import Set

SUPPORTED_AGENTS = {
    # Decision / aggregation
    "final_refer":  "agents.agent_sets.aggregation.final_refer",
    # Math / reasoning
    "math_solver":  "agents.agent_sets.math.math_solver",
    # Multi-domain knowledge / QA
    "analyze_agent": "agents.agent_sets.analysis.analyze_agent",
    # Coding
    "code_writing": "agents.agent_sets.coding.code_writing",
}


def validate_agent_types(requested_type: Set[str]) -> None:
    """Raise if any requested type is not supported."""
    for t in requested_type:
        if t not in SUPPORTED_AGENTS:
            raise ValueError(
                f"Agent type '{t}' not supported. "
                f"Supported types: {list(SUPPORTED_AGENTS.keys())}"
            )


def load_agent_builder(agent_type):
    """Return the build_agent function for a given agent_type."""
    try:
        module_path = SUPPORTED_AGENTS[agent_type]
    except KeyError:
        raise ValueError(
            f"Agent type '{agent_type}' not supported. "
            f"Supported types: {list(SUPPORTED_AGENTS.keys())}"
        )

    module = importlib.import_module(module_path)
    return module.build_agent




