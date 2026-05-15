"""Compare Paramora benchmark JSON reports.

The timing scripts can write either a single report object or a list of report
objects. This helper compares two result files by scenario and highlights
microseconds-per-operation changes.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class StoredReport:
    """Normalized stored benchmark report."""

    scenario: str
    best_us_per_op: float
    best_ops_per_second: float


@dataclass(frozen=True, slots=True)
class Comparison:
    """One scenario comparison between baseline and candidate results."""

    scenario: str
    baseline_us: float
    candidate_us: float

    @property
    def delta_us(self) -> float:
        """Return candidate minus baseline in microseconds per operation."""
        return self.candidate_us - self.baseline_us

    @property
    def percent_change(self) -> float:
        """Return percentage change relative to the baseline."""
        return (self.delta_us / self.baseline_us) * 100


def load_reports(path: Path) -> dict[str, StoredReport]:
    """Load benchmark reports from a JSON file."""
    raw_payload: Any = json.loads(path.read_text(encoding="utf-8"))
    raw_reports = raw_payload if isinstance(raw_payload, list) else [raw_payload]
    reports: dict[str, StoredReport] = {}
    for raw_report in raw_reports:
        if not isinstance(raw_report, dict):
            raise SystemExit(f"Invalid benchmark report in {path}.")
        report = _parse_report(raw_report, path)
        reports[report.scenario] = report
    return reports


def _parse_report(raw_report: Mapping[str, Any], path: Path) -> StoredReport:
    scenario = raw_report.get("scenario")
    best_us_per_op = raw_report.get("best_us_per_op")
    best_ops_per_second = raw_report.get("best_ops_per_second")
    if not isinstance(scenario, str):
        raise SystemExit(f"Missing scenario in {path}.")
    if not isinstance(best_us_per_op, int | float):
        raise SystemExit(f"Missing best_us_per_op for {scenario!r} in {path}.")
    if not isinstance(best_ops_per_second, int | float):
        raise SystemExit(f"Missing best_ops_per_second for {scenario!r} in {path}.")
    return StoredReport(
        scenario=scenario,
        best_us_per_op=float(best_us_per_op),
        best_ops_per_second=float(best_ops_per_second),
    )


def compare_reports(
    baseline: Mapping[str, StoredReport],
    candidate: Mapping[str, StoredReport],
) -> list[Comparison]:
    """Compare matching scenarios from two report sets."""
    comparisons: list[Comparison] = []
    for scenario in sorted(baseline.keys() & candidate.keys()):
        comparisons.append(
            Comparison(
                scenario=scenario,
                baseline_us=baseline[scenario].best_us_per_op,
                candidate_us=candidate[scenario].best_us_per_op,
            )
        )
    return comparisons


def print_comparisons(comparisons: Sequence[Comparison]) -> None:
    """Print benchmark comparisons."""
    if not comparisons:
        print("No matching scenarios found.")
        return
    print("scenario | baseline µs/op | candidate µs/op | delta µs | change")
    print("--- | ---: | ---: | ---: | ---:")
    for comparison in comparisons:
        print(
            f"{comparison.scenario} | "
            f"{comparison.baseline_us:.2f} | "
            f"{comparison.candidate_us:.2f} | "
            f"{comparison.delta_us:+.2f} | "
            f"{comparison.percent_change:+.2f}%"
        )


def parse_args(argv: Sequence[str]) -> tuple[Path, Path]:
    """Parse comparison CLI arguments."""
    if len(argv) != 2 or argv[0] in {"-h", "--help"}:
        print_help()
        raise SystemExit(0 if argv and argv[0] in {"-h", "--help"} else 2)
    return Path(argv[0]), Path(argv[1])


def print_help() -> None:
    """Print benchmark comparison help."""
    print("Usage: python benchmarks/compare_results.py BASELINE.json CANDIDATE.json")


def main(argv: Sequence[str] | None = None) -> None:
    """Compare two benchmark result files."""
    baseline_path, candidate_path = parse_args(sys.argv[1:] if argv is None else argv)
    baseline = load_reports(baseline_path)
    candidate = load_reports(candidate_path)
    comparisons = compare_reports(baseline, candidate)
    print_comparisons(comparisons)


if __name__ == "__main__":
    main()
