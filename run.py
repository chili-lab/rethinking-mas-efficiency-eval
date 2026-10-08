"""Run a MAS on one or more questions and report its answers.

Usage:
    python run.py --mas examples/star_math --question "A shop sells pens at $3 each ..."
    python run.py --mas examples/star_math --questions examples/questions.txt

Each question is answered by the last agent of the MAS. Results go to
results/<mas folder name>/results.json (or --output), one record per question.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from core.engine import MASEngine
from core.log import get_logger, setup_logging_to_file
from core.mas import MASExperiment


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run a MAS on one or more questions.")
    p.add_argument("--mas", required=True, help="MAS folder with topology.json, agents.json, meta.json.")
    p.add_argument("--question", action="append", help="A question to answer (repeatable).")
    p.add_argument("--questions", help="Text file with one question per line.")
    p.add_argument("--output", help="Output folder (default: results/<mas folder name>).")
    return p.parse_args()


def _read_questions(args: argparse.Namespace) -> list[str]:
    questions = list(args.question or [])
    if args.questions:
        lines = Path(args.questions).read_text(encoding="utf-8").splitlines()
        questions += [line.strip() for line in lines if line.strip()]
    if not questions:
        raise SystemExit("Give at least one --question or a --questions file.")
    return questions


async def _run(args: argparse.Namespace) -> None:
    exp = MASExperiment.from_dir(args.mas)
    questions = _read_questions(args)
    output_dir = Path(args.output) if args.output else Path("results") / exp.exp_dir.name
    log = get_logger()  # console handler first; setup_logging_to_file only adds the file
    setup_logging_to_file(output_dir)
    log.info(exp.summary())

    engine = MASEngine(default_llm=exp.meta.get("default_llm"))
    flow = engine.compile(exp.topology, exp.agent_types)

    records: list[dict[str, Any]] = []
    for i, question in enumerate(questions, start=1):
        await flow.reset()
        result = await engine.run(flow, task=question)
        messages = getattr(result, "messages", None) or []
        answer = str(getattr(messages[-1], "content", "")) if messages else ""

        records.append({"question": question, "answer": answer})
        log.info(f"\n----- Question {i}/{len(questions)} -----\n{question}")
        log.info(f"\n----- Answer -----\n{answer}\n")

    _write_json(output_dir / "results.json", records)
    log.info(f"Results saved to {output_dir / 'results.json'}")


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
