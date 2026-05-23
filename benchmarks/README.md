# Paramora benchmarks

This directory contains lightweight benchmark and profiling scripts for Paramora.
They intentionally use the public `Query(...)` API so results represent normal
application usage.

The benchmark suite is part of the development process. Use it when changing the
parser, compiled contracts, coercion, Mongo emission, SQL emission, or structured
error handling.

## Run one timing scenario

Use this when you want stable wall-clock measurements for one scenario:

```bash
uv run python benchmarks/bench_parse.py --scenario strict-mongo
```

Useful options:

```bash
uv run python benchmarks/bench_parse.py --scenario strict-mongo
uv run python benchmarks/bench_parse.py --scenario strict-sql
uv run python benchmarks/bench_parse.py --scenario strict-postgres
uv run python benchmarks/bench_parse.py --scenario sqlite-statement
uv run python benchmarks/bench_parse.py --scenario postgres-statement
uv run python benchmarks/bench_parse.py --scenario loose-mongo
uv run python benchmarks/bench_parse.py --scenario invalid-strict
uv run python benchmarks/bench_parse.py --scenario emit-mongo
uv run python benchmarks/bench_parse.py --scenario emit-sql
uv run python benchmarks/bench_parse.py --iterations 200000 --repeats 9
uv run python benchmarks/bench_parse.py --json benchmark-results/strict-mongo.json
```

## Run every timing scenario

Use this before and after performance-sensitive changes:

```bash
uv run python benchmarks/bench_all.py --json benchmark-results/before.json
# make the change
uv run python benchmarks/bench_all.py --json benchmark-results/after.json
uv run python benchmarks/compare_results.py benchmark-results/before.json benchmark-results/after.json
```

The comparison script prints microseconds per operation and percentage change for
matching scenarios.

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
- `strict-sql`: strict contract parse plus SQLite-style SQL emission.
- `strict-postgres`: strict contract parse plus PostgreSQL-style SQL emission.
- `sqlite-statement`: strict parse plus SQLite `SELECT` statement composition.
- `postgres-statement`: strict parse plus PostgreSQL `SELECT` statement composition.
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
