# Paramora benchmarks

This directory contains lightweight benchmark and profiling scripts for Paramora.
They intentionally use the public `Query(...)` API so results represent normal
application usage.

## Timing benchmark

Use this when you want stable wall-clock measurements:

```bash
uv run python benchmarks/bench_parse.py
```

Useful options:

```bash
uv run python benchmarks/bench_parse.py --scenario strict-mongo
uv run python benchmarks/bench_parse.py --scenario strict-sql
uv run python benchmarks/bench_parse.py --scenario loose-mongo
uv run python benchmarks/bench_parse.py --scenario invalid-strict
uv run python benchmarks/bench_parse.py --scenario emit-mongo
uv run python benchmarks/bench_parse.py --scenario emit-sql
uv run python benchmarks/bench_parse.py --iterations 200000 --repeats 9
uv run python benchmarks/bench_parse.py --json benchmark-results/strict-mongo.json
```

## cProfile hotspot report

Use this when you want to know where time is spent:

```bash
uv run python benchmarks/profile_parse.py --scenario strict-mongo
```

Useful options:

```bash
uv run python benchmarks/profile_parse.py --iterations 500000 --limit 40
uv run python benchmarks/profile_parse.py --sort tottime
```

## Scenarios

- `strict-mongo`: strict contract parse plus Mongo emission.
- `strict-sql`: strict contract parse plus SQL emission.
- `loose-mongo`: loose-mode parse plus Mongo emission.
- `invalid-strict`: strict-mode invalid query validation path.
- `emit-mongo`: Mongo emission from a prebuilt AST.
- `emit-sql`: SQL emission from a prebuilt AST.

## Interpreting results

The timing script reports best/mean/median/stdev, microseconds per operation, and
operations per second. The best repeat is usually the least noisy single-run
number. The mean and standard deviation help identify unstable benchmark runs.

Use the cProfile script to find hotspots before optimizing. Do not optimize based
on one timing number alone.
