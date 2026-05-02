"""Profile Paramora query parsing and backend emission with cProfile.

Use this script to identify hotspots. For stable wall-clock timing, use
``benchmarks/bench_parse.py`` instead.
"""

from __future__ import annotations

import cProfile
import pstats
import sys
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typing import TYPE_CHECKING

from benchmarks.fixtures import DEFAULT_SCENARIO, SCENARIOS

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class ProfileArgs:
    """Parsed cProfile benchmark arguments."""

    scenario: str
    iterations: int
    limit: int
    sort_by: str


def profile_scenario(args: ProfileArgs) -> str:
    """Run cProfile for a scenario and return the formatted stats report."""
    scenario = SCENARIOS[args.scenario]
    runner = scenario.runner
    profiler = cProfile.Profile()

    profiler.enable()
    last_result: object = None
    for _ in range(args.iterations):
        last_result = runner()
    profiler.disable()

    if last_result is None:
        raise RuntimeError("Benchmark runner unexpectedly returned None.")

    output = StringIO()
    stats = pstats.Stats(profiler, stream=output).strip_dirs().sort_stats(args.sort_by)
    stats.print_stats(args.limit)
    return output.getvalue()


def parse_args(argv: Sequence[str]) -> ProfileArgs:
    """Parse cProfile CLI arguments."""
    scenario = DEFAULT_SCENARIO
    iterations = 50_000
    limit = 30
    sort_by = "cumtime"

    index = 0
    while index < len(argv):
        option = argv[index]
        if option in {"-h", "--help"}:
            print_help()
            raise SystemExit(0)
        if option == "--scenario":
            index += 1
            scenario = _read_value(argv, index, option)
        elif option == "--iterations":
            index += 1
            iterations = _read_positive_int(argv, index, option)
        elif option == "--limit":
            index += 1
            limit = _read_positive_int(argv, index, option)
        elif option == "--sort":
            index += 1
            sort_by = _read_value(argv, index, option)
        else:
            raise SystemExit(f"Unknown option: {option}")
        index += 1

    if scenario not in SCENARIOS:
        names = ", ".join(sorted(SCENARIOS))
        raise SystemExit(f"Unknown scenario {scenario!r}. Available: {names}")

    return ProfileArgs(
        scenario=scenario,
        iterations=iterations,
        limit=limit,
        sort_by=sort_by,
    )


def _read_value(argv: Sequence[str], index: int, option: str) -> str:
    if index >= len(argv):
        raise SystemExit(f"{option} requires a value.")
    return argv[index]


def _read_positive_int(argv: Sequence[str], index: int, option: str) -> int:
    raw_value = _read_value(argv, index, option)
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise SystemExit(f"{option} must be an integer.") from exc
    if value <= 0:
        raise SystemExit(f"{option} must be greater than zero.")
    return value


def print_help() -> None:
    """Print cProfile benchmark help."""
    names = ", ".join(sorted(SCENARIOS))
    print(
        "Usage: python benchmarks/profile_parse.py "
        "[--scenario NAME] [--iterations N] [--limit N] [--sort FIELD]"
    )
    print(f"Available scenarios: {names}")
    print("Common sort fields: cumtime, tottime, calls, ncalls")


def main(argv: Sequence[str] | None = None) -> None:
    """Run the cProfile benchmark CLI."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    print(profile_scenario(args))


if __name__ == "__main__":
    main()
