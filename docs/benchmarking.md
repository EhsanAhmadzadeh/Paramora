# Benchmarking and profiling

Paramora includes dependency-light benchmark scripts so performance work can be
measured instead of guessed. The scripts use the public `Query(...)` API and
cover the parser, validation path, MongoDB emission, and raw SQL emission.

## Why benchmarks exist

Paramora sits in the HTTP request path. It should be fast enough that database
I/O, JSON serialization, and application logic dominate request latency. At the
same time, the parser and emitters should stay measurable so regressions are
caught early.

Use benchmarks when you change:

- query parsing
- type coercion
- strict/loose validation
- MongoDB emission
- SQL emission
- error handling on invalid requests
- compiled contract metadata

## Run one scenario

```bash
uv run python benchmarks/bench_parse.py --scenario strict-mongo
```

Useful scenarios:

- `strict-mongo`: strict contract parse plus Mongo emission.
- `strict-sql`: strict contract parse plus SQLite-style SQL emission.
- `loose-mongo`: loose-mode parse plus Mongo emission.
- `invalid-strict`: invalid strict request that produces structured errors.
- `emit-mongo`: Mongo emission from a prebuilt AST.
- `emit-sql`: SQL emission from a prebuilt AST.

## Run the full suite

```bash
uv run python benchmarks/bench_all.py
```

For repeatable comparisons, write JSON results:

```bash
uv run python benchmarks/bench_all.py --json benchmark-results/before.json
# make your change
uv run python benchmarks/bench_all.py --json benchmark-results/after.json
uv run python benchmarks/compare_results.py benchmark-results/before.json benchmark-results/after.json
```

The comparison output shows microseconds per operation and percentage change per
scenario.

## Use cProfile for hotspots

Timing tells you that something changed. cProfile tells you where time is going.

```bash
uv run python benchmarks/profile_parse.py --scenario strict-sql --iterations 500000 --limit 40
```

Common sort modes:

```bash
uv run python benchmarks/profile_parse.py --sort cumtime
uv run python benchmarks/profile_parse.py --sort tottime
uv run python benchmarks/profile_parse.py --sort calls
```

## How to interpret benchmark results

The timing script reports:

- best seconds
- mean seconds
- median seconds
- standard deviation
- best microseconds per operation
- best operations per second

The best run is useful for comparing the lower-noise path. The mean, median, and
standard deviation help you detect noisy measurements. Run benchmarks on the same
machine, with the same Python version, when comparing two commits.

## Performance policy

Performance work should follow this order:

1. Add or update a benchmark scenario if the behavior is not measured.
2. Run the benchmark before the change.
3. Make the change.
4. Run the benchmark after the change.
5. Use cProfile if the result is unexpectedly slower.
6. Document meaningful wins or tradeoffs in the pull request.

Do not make code harder to maintain for tiny speedups unless the hotspot is
important and measured.

## Future Rust hotspots

Rust may become useful later for stable, hot internals such as parsing or value
coercion. Before that happens, the Python API, AST, error model, and benchmark
suite should be stable. Any Rust-backed module should keep typed Python-facing
interfaces, including `.pyi` files where appropriate.
