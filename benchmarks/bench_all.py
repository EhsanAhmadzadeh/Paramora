"""Run every Paramora benchmark scenario and optionally write JSON results."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.bench_parse import TimingArgs, TimingReport, build_report, print_report
from benchmarks.fixtures import SCENARIOS

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class SuiteArgs:
    """Parsed benchmark-suite arguments."""

    iterations: int
    repeats: int
    warmups: int
    json_path: Path | None


def run_suite(args: SuiteArgs) -> list[TimingReport]:
    """Run all registered benchmark scenarios."""
    reports: list[TimingReport] = []
    for scenario_name in sorted(SCENARIOS):
        report = build_report(
            TimingArgs(
                scenario=scenario_name,
                iterations=args.iterations,
                repeats=args.repeats,
                warmups=args.warmups,
                json_path=None,
            )
        )
        reports.append(report)
    return reports


def print_suite(reports: Sequence[TimingReport]) -> None:
    """Print a compact suite report."""
    for index, report in enumerate(reports):
        if index:
            print()
        print_report(report)


def write_json_reports(reports: Sequence[TimingReport], path: Path) -> None:
    """Write benchmark suite results as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [report.to_json_dict() for report in reports]
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(serialized, encoding="utf-8")


def parse_args(argv: Sequence[str]) -> SuiteArgs:
    """Parse benchmark-suite CLI arguments."""
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
        if option == "--iterations":
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

    return SuiteArgs(
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
    """Print benchmark-suite help."""
    print(
        "Usage: python benchmarks/bench_all.py "
        "[--iterations N] [--repeats N] [--warmups N] [--json PATH]"
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Run all benchmark scenarios."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    reports = run_suite(args)
    print_suite(reports)
    if args.json_path is not None:
        write_json_reports(reports, args.json_path)


if __name__ == "__main__":
    main()
