from typing import Any
import os
import sys

# ensure project root is on sys.path so that "agents" and "core" can be imported
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.ui import Console
from autogen_agentchat.agents import (
    MessageFilterAgent,
    MessageFilterConfig,
    PerSourceFilter,
)
from autogen_core.models import ModelFamily, ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient
from agents import load_agent_builder

from core.topology import Topology

from dotenv import load_dotenv


def _default_model_info_for_custom_endpoint() -> ModelInfo:
    """ModelInfo for OpenAI-compatible custom endpoints (e.g. vLLM) when model name is not in autogen's list."""
    return {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": False,
        "multiple_system_messages": True,
    }


class _ForcedToolChoiceClient:
    """Thin wrapper around OpenAIChatCompletionClient that injects tool_choice='required'
    only for calls where tools are actually provided.

    Background: AutoGen bakes create_args (including tool_choice) into the client at
    construction time and passes them to *every* model call — including the reflection
    call in _reflect_on_tool_use_flow which sends no tools.  OpenAI rejects
    tool_choice='required' when the tools list is empty (HTTP 400).

    This wrapper intercepts create() / create_stream() and upgrades tool_choice to
    "required" only when tools are non-empty, leaving the reflection call (tools=[])
    untouched so it goes out as tool_choice='none' (set explicitly by AutoGen).
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    async def create(self, messages: Any, *, tools: Any = [], tool_choice: Any = "auto", **kwargs: Any) -> Any:
        if tools:
            tool_choice = "required"
        return await self._client.create(messages, tools=tools, tool_choice=tool_choice, **kwargs)

    async def create_stream(self, messages: Any, *, tools: Any = [], tool_choice: Any = "auto", **kwargs: Any) -> Any:
        async for item in self._client.create_stream(messages, tools=tools, tool_choice=tool_choice, **kwargs):
            yield item

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


def _create_client_from_llm_config(llm: dict[str, Any]) -> Any:
    """Build OpenAIChatCompletionClient from a config dict.

    Recognised keys (all optional except 'model'):
      model, base_url, api_key, max_tokens
      parallel_tool_calls – bool
      temperature, seed, … any other key in OpenAI's create_kwargs allowlist

    NOTE: 'tool_choice' is intentionally NOT passed to the constructor.
    AutoGen's _process_create_args already writes tool_choice into every API call
    when tools are present. Baking it into self._create_args causes it to appear
    in reflection calls (no tools) → OpenAI 400.  Use _ForcedToolChoiceClient
    wrapper instead (handled in compile()).

    Legacy key:
      extra_create_args – dict whose entries are *flattened* into the top-level kwargs
                          so that AutoGen's _create_args_from_config picks them up.
                          (Nested dicts are NOT supported by AutoGen's config parser.)
    """
    load_dotenv()
    model = llm.get("model")
    if not model:
        raise ValueError("LLM config must have 'model'. Set meta.default_llm or agents[].llm.")
    base_url = llm.get("base_url") or os.getenv("OPENAI_BASE_URL")
    api_key = llm.get("api_key") if llm.get("api_key") is not None else os.getenv("OPENAI_API_KEY")
    # Cap generation length so a single turn doesn't hang (default 2048; override via llm.max_tokens)
    max_tokens = llm.get("max_tokens", 2048)
    kwargs: dict[str, Any] = {"model": model, "api_key": api_key, "max_tokens": max_tokens}
    if base_url:
        kwargs["base_url"] = base_url
        kwargs["model_info"] = _default_model_info_for_custom_endpoint()

    # Pass-through of recognised OpenAI create-kwargs — but NOT tool_choice (see docstring).
    _PASSTHROUGH = {"parallel_tool_calls", "temperature", "seed",
                    "top_p", "frequency_penalty", "presence_penalty", "reasoning_effort"}
    for key in _PASSTHROUGH:
        if key in llm:
            kwargs[key] = llm[key]

    # Legacy: extra_create_args dict → flatten into top-level kwargs.
    # AutoGen's _create_args_from_config filters by a fixed allowlist, so values must
    # be at the top level, NOT nested under an "extra_create_args" key.
    # Skip tool_choice here too — handled via wrapper.
    for k, v in (llm.get("extra_create_args") or {}).items():
        if k == "tool_choice":
            continue
        kwargs.setdefault(k, v)  # top-level keys already set above take precedence

    return OpenAIChatCompletionClient(**kwargs)


class MASEngine:
    def __init__(self, default_llm: dict[str, Any] | None = None):
        """Create engine. Per-agent LLM is default_llm merged with agent's llm in compile()."""
        load_dotenv()
        self._default_llm = default_llm or {}

    def compile(self, topology: Topology, agent_types: list[dict[str, Any]]) -> GraphFlow:
        topology.validate()
        T = topology.num_rounds()
        N = len(agent_types)
        node_masks = topology.node_masks
        temporal_masks = topology.temporal_masks
        spatial_masks = topology.spatial_masks

        builder = DiGraphBuilder()
        nodes = {}

        for t in range(T):
            for i, info in enumerate(agent_types):
                if node_masks[t][i] == 0:
                    continue

                # Merge default_llm with any per-agent llm overrides.
                # The agent llm dict may be partial (e.g. only extra_create_args),
                # so we always shallow-merge it on top of default_llm regardless of
                # whether it carries a model field.
                agent_llm = info.get("llm") or {}
                effective_llm = {**self._default_llm, **agent_llm}
                if not effective_llm.get("model"):
                    raise ValueError(
                        f"Agent {info.get('name', i)} has no 'model'. Set meta.default_llm or agents[].llm with a valid model."
                    )

                client = _create_client_from_llm_config(effective_llm)

                # Top-level "tool_choice" in agents.json ("auto" | "required" | "none").
                # "required" → wrap the client so it injects tool_choice="required" only
                # when tools are actually present in the API call (safe for reflection calls).
                # Other values ("auto", absent) → default AutoGen behaviour, no wrapper needed.
                tool_choice = info.get("tool_choice")
                if tool_choice == "required":
                    client = _ForcedToolChoiceClient(client)

                name = f"{info['name']}_t{t}"
                agent = load_agent_builder(info["agent_type"])(name, client, info)

                nodes[(t, i)] = agent
                builder.add_node(agent)

        # Spatial: within same round
        for t in range(T):
            for u in range(N):
                for v in range(N):
                    if spatial_masks[t][u][v] == 1:
                        if (t, u) in nodes and (t, v) in nodes:
                            builder.add_edge(nodes[(t, u)], nodes[(t, v)])

        # Temporal: from t-1 -> t only
        for t in range(1, T):
            for u in range(N):
                for v in range(N):
                    if temporal_masks[t][u][v] == 1:
                        if (t-1, u) in nodes and (t, v) in nodes:
                            builder.add_edge(nodes[(t-1, u)], nodes[(t, v)])

        # ----------------------------
        # Strict observation control
        # ----------------------------
        # Compute allowed predecessor sources for each node
        allowed_sources = {}

        for (t, i), agent in nodes.items():
            srcs = []

            # spatial predecessors
            for u in range(N):
                if spatial_masks[t][u][i] == 1 and (t, u) in nodes:
                    srcs.append(nodes[(t, u)].name)

            # temporal predecessors
            if t > 0:
                for u in range(N):
                    if temporal_masks[t][u][i] == 1 and (t-1, u) in nodes:
                        srcs.append(nodes[(t-1, u)].name)

            allowed_sources[agent.name] = list(set(srcs))

        # Ensure every agent can also see the latest user message.
        # In the default GraphFlow, the initial task is injected as a message
        # from source "user", so we always whitelist that source here.
        for agent_name, srcs in allowed_sources.items():
            if "user" not in srcs:
                srcs.append("user")
            allowed_sources[agent_name] = srcs

        # Wrap agents with message filters
        builder2 = DiGraphBuilder()
        wrapped = {}

        for agent in nodes.values():
            filters = [
                PerSourceFilter(source=s, position="last", count=1)
                for s in allowed_sources[agent.name]
            ]

            w = MessageFilterAgent(
                name=agent.name,
                wrapped_agent=agent,
                filter=MessageFilterConfig(per_source=filters),
            )

            wrapped[agent.name] = w
            builder2.add_node(w)

        # Re-add edges using wrapped agents
        for t in range(T):
            for u in range(N):
                for v in range(N):
                    if spatial_masks[t][u][v] == 1:
                        if (t, u) in nodes and (t, v) in nodes:
                            src_name = nodes[(t, u)].name
                            builder2.add_edge(
                                wrapped[src_name],
                                wrapped[nodes[(t, v)].name],
                            )

        for t in range(1, T):
            for u in range(N):
                for v in range(N):
                    if temporal_masks[t][u][v] == 1:
                        if (t-1, u) in nodes and (t, v) in nodes:
                            src_name = nodes[(t-1, u)].name
                            builder2.add_edge(
                                wrapped[src_name],
                                wrapped[nodes[(t, v)].name],
                            )

        return GraphFlow(
            participants=builder2.get_participants(),
            graph=builder2.build(),
        )


    async def run(self, flow: GraphFlow, task: str):
        result = await flow.run(task=task)
        return result
