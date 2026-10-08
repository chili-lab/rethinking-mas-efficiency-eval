"""MASExperiment — loads a MAS definition from a folder.

MAS folder layout:
    <exp_dir>/
        topology.json      num_rounds, num_nodes, spatial_masks, temporal_masks, node_masks
        agents.json        list of {name, agent_type, role?, llm?: {model?, base_url?, api_key?}}
        meta.json          name, description, default_llm?: {model, base_url?, api_key?}, ...

Usage:
    exp = MASExperiment.from_dir("examples/star_math")
    engine = MASEngine(default_llm=exp.meta.get("default_llm"))
    flow = engine.compile(exp.topology, exp.agent_types)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.topology import Topology


_REQUIRED_FILES = ("topology.json", "agents.json", "meta.json")

_REQUIRED_TOPOLOGY_KEYS = ("num_rounds", "num_nodes", "spatial_masks", "temporal_masks", "node_masks")


@dataclass
class MASExperiment:
    """Fully validated, self-contained MAS definition."""

    exp_dir: Path

    topology: Topology
    agent_types: list[dict[str, Any]]   # [{name, agent_type}, ...]

    meta: dict[str, Any]

    @classmethod
    def from_dir(cls, exp_dir: str | Path) -> "MASExperiment":
        """Load and validate a MAS from a definition folder."""
        exp_dir = Path(exp_dir).resolve()

        if not exp_dir.is_dir():
            raise FileNotFoundError(f"MAS directory not found: {exp_dir}")

        missing = [f for f in _REQUIRED_FILES if not (exp_dir / f).exists()]
        if missing:
            raise FileNotFoundError(
                f"Missing required files in {exp_dir}: {missing}"
            )

        topo_raw   = _load_json(exp_dir / "topology.json")
        agents_raw = _load_json(exp_dir / "agents.json")
        meta       = _load_json(exp_dir / "meta.json")

        # ---- validate topology keys ----
        for k in _REQUIRED_TOPOLOGY_KEYS:
            if k not in topo_raw:
                raise ValueError(f"topology.json is missing key: '{k}'")

        topology = Topology(
            spatial_masks  = topo_raw["spatial_masks"],
            temporal_masks = topo_raw["temporal_masks"],
            node_masks     = topo_raw["node_masks"],
        )
        topology.validate()

        # ---- validate agents list ----
        if not isinstance(agents_raw, list) or len(agents_raw) == 0:
            raise ValueError("agents.json must be a non-empty list of agent configs.")

        num_nodes = topo_raw["num_nodes"]
        if len(agents_raw) != num_nodes:
            raise ValueError(
                f"agents.json has {len(agents_raw)} entries but topology.num_nodes={num_nodes}."
            )

        for i, entry in enumerate(agents_raw):
            if "name" not in entry or "agent_type" not in entry:
                raise ValueError(
                    f"agents.json entry {i} must have 'name' and 'agent_type' keys."
                )

        return cls(
            exp_dir     = exp_dir,
            topology    = topology,
            agent_types = agents_raw,
            meta        = meta,
        )

    def summary(self) -> str:
        name  = self.meta.get("name", self.exp_dir.name)
        default_llm = self.meta.get("default_llm") or {}
        first_agent_llm = (self.agent_types[0].get("llm") or {}) if self.agent_types else {}
        model = default_llm.get("model") or first_agent_llm.get("model", "?")
        T     = self.topology.num_rounds()
        N     = len(self.agent_types)
        agents_str = ", ".join(
            f"{a['name']}({a['agent_type']})" for a in self.agent_types
        )
        return "\n".join([
            f"MAS        : {name}",
            f"Model      : {model}",
            f"Topology   : {T} round(s), {N} node(s)",
            f"Agents     : {agents_str}",
        ])


def _load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
