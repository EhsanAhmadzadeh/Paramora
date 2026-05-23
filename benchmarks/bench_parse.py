"""Run timing benchmarks for Paramora parser and emitters.

This script complements ``profile_parse.py``. Use this file when you want stable
wall-clock timings. Use ``profile_parse.py`` when you want a cProfile call graph
for hotspot investigation.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, stdev
from time import perf_counter_ns

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typing import TYPE_CHECKING

from benchmarks.fixtures import DEFAULT_SCENARIO, SCENARIOS, BenchmarkScenario

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class TimingArgs:
    """Parsed timing benchmark arguments."""

    scenario: str
    iterations: int
    repeats: int
    warmups: int
    json_path: Path | None


@dataclass(frozen=True, slots=True)
class TimingReport:
    """Benchmark timing report.

    Args:
        scenario: Scenario name.
        description: Scenario description.
        iterations: Iterations per repeat.
        repeats: Number of measured repeats.
        warmups: Number of unmeasured warmup runs.
        best_seconds: Fastest measured repeat.
        mean_seconds: Mean measured repeat time.
        median_seconds: Median measured repeat time.
        stdev_seconds: Sample standard deviation across repeats.
    """

    scenario: str
    description: str
    iterations: int
    repeats: int
    warmups: int
    best_seconds: float
    mean_seconds: float
    median_seconds: float
    stdev_seconds: float

    @property
    def best_us_per_op(self) -> float:
        """Return microseconds per operation for the best repeat."""
        return (self.best_seconds / self.iterations) * 1_000_000

    @property
    def best_ops_per_second(self) -> float:
        """Return operations per second for the best repeat."""
        return self.iterations / self.best_seconds

    def to_json_dict(self) -> dict[str, str | int | float]:
        """Return a JSON-serializable report dictionary."""
        return {
            "scenario": self.scenario,
            "description": self.description,
            "iterations": self.iterations,
            "repeats": self.repeats,
            "warmups": self.warmups,
            "best_seconds": self.best_seconds,
            "mean_seconds": self.mean_seconds,
            "median_seconds": self.median_seconds,
            "stdev_seconds": self.stdev_seconds,
            "best_us_per_op": self.best_us_per_op,
            "best_ops_per_second": self.best_ops_per_second,
        }


def run_iterations(scenario: BenchmarkScenario, iterations: int) -> float:
    """Run a scenario repeatedly and return elapsed seconds."""
    runner = scenario.runner
    started_at = perf_counter_ns()
    last_result: object = None
    for _ in range(iterations):
        last_result = runner()
    elapsed_ns = perf_counter_ns() - started_at
    if last_result is None:
        raise RuntimeError("Benchmark runner unexpectedly returned None.")
    return elapsed_ns / 1_000_000_000


def build_report(args: TimingArgs) -> TimingReport:
    """Run warmups and measured repeats for a timing benchmark."""
    scenario = SCENARIOS[args.scenario]

    for _ in range(args.warmups):
        run_iterations(scenario, args.iterations)

    measurements = [
        run_iterations(scenario, args.iterations) for _ in range(args.repeats)
    ]
    return TimingReport(
        scenario=scenario.name,
        description=scenario.description,
        iterations=args.iterations,
        repeats=args.repeats,
        warmups=args.warmups,
        best_seconds=min(measurements),
        mean_seconds=mean(measurements),
        median_seconds=median(measurements),
        stdev_seconds=stdev(measurements) if len(measurements) > 1 else 0.0,
    )


def print_report(report: TimingReport) -> None:
    """Print a human-readable timing report."""
    print(f"scenario: {report.scenario}")
    print(f"description: {report.description}")
    print(f"iterations: {report.iterations:,}")
    print(f"repeats: {report.repeats}")
    print(f"warmups: {report.warmups}")
    print(f"best: {report.best_seconds:.6f}s")
    print(f"mean: {report.mean_seconds:.6f}s")
    print(f"median: {report.median_seconds:.6f}s")
    print(f"stdev: {report.stdev_seconds:.6f}s")
    print(f"best/op: {report.best_us_per_op:.2f} µs")
    print(f"best throughput: {report.best_ops_per_second:,.0f} ops/s")


def write_json_report(report: TimingReport, path: Path) -> None:
    """Write a machine-readable timing report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_json_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: Sequence[str]) -> TimingArgs:
    """Parse benchmark CLI arguments without introducing untyped argparse state."""
    scenario = DEFAULT_SCENARIO
    iterations = 100_000
    repeats = 7
    warmups = 2
    json_path: Path | None = None

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
        elif option == "--repeats":
            index += 1
            repeats = _read_positive_int(argv, index, option)
        elif option == "--warmups":
            index += 1
            warmups = _read_non_negative_int(argv, index, option)
        elif option == "--json":
            index += 1
            json_path = Path(_read_value(argv, index, option))
        else:
            raise SystemExit(f"Unknown option: {option}")
        index += 1

    if scenario not in SCENARIOS:
        names = ", ".join(sorted(SCENARIOS))
        raise SystemExit(f"Unknown scenario {scenario!r}. Available: {names}")

    return TimingArgs(
        scenario=scenario,
        iterations=iterations,
        repeats=repeats,
        warmups=warmups,
        json_path=json_path,
    )


def _read_value(argv: Sequence[str], index: int, option: str) -> str:
    if index >= len(argv):
        raise SystemExit(f"{option} requires a value.")
    return argv[index]


def _read_positive_int(argv: Sequence[str], index: int, option: str) -> int:
    value = _read_non_negative_int(argv, index, option)
    if value <= 0:
        raise SystemExit(f"{option} must be greater than zero.")
    return value


def _read_non_negative_int(argv: Sequence[str], index: int, option: str) -> int:
    raw_value = _read_value(argv, index, option)
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise SystemExit(f"{option} must be an integer.") from exc
    if value < 0:
        raise SystemExit(f"{option} must be non-negative.")
    return value


def print_help() -> None:
    """Print benchmark CLI help."""
    names = ", ".join(sorted(SCENARIOS))
    print(
        "Usage: python benchmarks/bench_parse.py "
        "[--scenario NAME] [--iterations N] [--repeats N] "
        "[--warmups N] [--json PATH]"
    )
    print(f"Available scenarios: {names}")


def main(argv: Sequence[str] | None = None) -> None:
    """Run the timing benchmark CLI."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_report(args)
    print_report(report)
    if args.json_path is not None:
        write_json_report(report, args.json_path)


if __name__ == "__main__":
    main()
