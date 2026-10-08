# Rethinking the Evaluation of Efficiency Methods for Multi-Agent Systems

A demo of the MAS engine from our EMNLP 2026 paper. Define a MAS, give it questions, and get its answers.

## Installation

```bash
conda create -n optimas_demo -y python=3.10
conda activate optimas_demo
pip install -r requirements.txt
```

## Quick start

1. Serve the example's model with any OpenAI-compatible server:

```bash
vllm serve Qwen/Qwen3-4B-Instruct-2507 --port 8000
```

The example MAS points to `http://127.0.0.1:8000/v1`. To use another server or model, edit `default_llm` in `examples/star_math/meta.json`.

2. Run the example MAS on one question, or on a file with one question per line:

```bash
python run.py --mas examples/star_math --question 'Tom has 3 times as many marbles as Jerry. Together they have 48 marbles. How many marbles does Tom have?'
python run.py --mas examples/star_math --questions examples/questions.txt
```

The answers are printed and saved to `results/star_math/results.json`. Use `--output <dir>` to save them elsewhere.

## MAS format

A MAS is a folder with three files. In the example `examples/star_math/`, 5 math agents each send their answer to a decision agent, over 2 rounds; in round 2, every agent also sees its own answer from round 1.

| File              | Content                                                                                           |
| ----------------- | ------------------------------------------------------------------------------------------------- |
| `topology.json` | `num_rounds`, `num_nodes`, and three masks per round                                          |
| `agents.json`   | one entry per node:`name`, `agent_type`, and optional `role`                                |
| `meta.json`     | `default_llm`: `model`, `base_url`, `api_key`, and optional `max_tokens` (default 2048) |

The masks define the topology:

- `spatial_masks[t][i][j] = 1`: agent i sends its output to agent j in round t. Each round must be a DAG (upper-triangular).
- `temporal_masks[t][i][j] = 1`: agent i's output from round t−1 goes to agent j in round t.
- `node_masks[t][i] = 1`: agent i is active in round t.

The last agent's output in the final round is the MAS answer. The runner rejects invalid topologies before running.

`agent_type` is one of `math_solver`, `analyze_agent`, `code_writing` and `final_refer`. The roles each type accepts are the keys of `ROLE_DESCRIPTION` in `agents/prompt_sets/` (`math.py`, `analysis.py`, `coding.py`); an unknown role falls back to the type's default role. `final_refer` takes no role.

## License

[Apache License 2.0](LICENSE).
