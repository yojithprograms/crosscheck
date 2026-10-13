"""Runs the whole pipeline in order.

    python -m crosscheck_pipeline.run_all              # every step
    python -m crosscheck_pipeline.run_all --from s05   # resume from a step

Step s09 (traffic volume) runs before s07 (training) because the model uses it, and only when
config.USE_AADT is on. The exports are checked at the end.
"""
from __future__ import annotations

import argparse
import importlib
import time

from crosscheck_pipeline import config

# (id, module) in the order they must run.
STEPS: list[tuple[str, str]] = [
    ("s01", "crosscheck_pipeline.s01_schools"),
    ("s02", "crosscheck_pipeline.s02_crashes"),
    ("s03", "crosscheck_pipeline.s03_osm"),
    ("s04", "crosscheck_pipeline.s04_sidewalks"),
    ("s05", "crosscheck_pipeline.s05_segments"),
    ("s06", "crosscheck_pipeline.s06_assign"),
    ("s09", "crosscheck_pipeline.s09_aadt"),
    ("s07", "crosscheck_pipeline.s07_train"),
    ("s08", "crosscheck_pipeline.s08_score"),
    ("s10", "crosscheck_pipeline.s10_school_graphs"),
    ("s11", "crosscheck_pipeline.s11_exports"),
    ("validate", "crosscheck_pipeline.validate_exports"),
]


def steps_to_run(first: str | None = None, use_aadt: bool = config.USE_AADT) -> list[tuple[str, str]]:
    """The steps from `first` onward (in run order), skipping s09 when traffic volume is off."""
    ids = [step_id for step_id, _ in STEPS]
    if first is not None and first not in ids:
        raise ValueError(f"unknown step {first!r}; choose one of {ids}")
    start = ids.index(first) if first else 0
    return [(i, m) for i, m in STEPS[start:] if use_aadt or i != "s09"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CrossCheck data pipeline.")
    parser.add_argument("--from", dest="first", help="resume from this step (for example s05)")
    args = parser.parse_args()
    for step_id, module_name in steps_to_run(args.first):
        print(f"\n===== {step_id}: {module_name} =====", flush=True)
        started = time.time()
        importlib.import_module(module_name).main()
        print(f"----- {step_id} done in {time.time() - started:.0f}s", flush=True)


if __name__ == "__main__":
    main()
