"""Central logging for the benchmark. Logs go to console and optionally to output_dir/exp.log."""

from __future__ import annotations

import logging
from pathlib import Path

LOGGER_NAME = "bench"


def get_logger() -> logging.Logger:
    """Return the bench logger. Console handler is added once if missing."""
    log = logging.getLogger(LOGGER_NAME)
    if not log.handlers:
        log.setLevel(logging.DEBUG)
        h = logging.StreamHandler()
        h.setLevel(logging.INFO)
        h.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(h)
    return log


def setup_logging_to_file(output_dir: Path) -> None:
    """Add a FileHandler so logs are also written to output_dir/exp.log."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger(LOGGER_NAME)
    # Remove any existing file handlers we added (avoid duplicates across runs)
    for h in log.handlers[:]:
        if isinstance(h, logging.FileHandler):
            h.close()
            log.removeHandler(h)
    fh = logging.FileHandler(output_dir / "exp.log", mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    log.addHandler(fh)
