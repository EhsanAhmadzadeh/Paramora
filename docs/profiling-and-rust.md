# Benchmarking, profiling, and future Rust hotspots

Paramora should stay fast, but performance work should be evidence-driven. The
package currently keeps the parser and emitters pure Python because that gives
users a simple installation path and keeps the public API easy to evolve.

Use benchmarks for two different jobs:

- **Timing benchmarks** answer: "How fast is this scenario?"
- **cProfile reports** answer: "Where is time being spent?"

Do not optimize based on a single number. Measure before and after each change.

## Timing benchmark

Use `benchmarks/bench_parse.py` for repeatable wall-clock measurements:

```bash
uv run python benchmarks/bench_parse.py
```

Default behavior measures strict query parsing plus MongoDB emission.

Useful examples:

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

The timing report includes:

- best measured repeat
- mean repeat time
- median repeat time
- standard deviation
- microseconds per operation
- operations per second

The **best** repeat is useful for comparing implementation changes because it is
usually the least affected by scheduler noise. The **mean** and **standard
deviation** help reveal noisy runs.

## cProfile hotspot report

Use `benchmarks/profile_parse.py` when you need call-level hotspot data:

```bash
uv run python benchmarks/profile_parse.py --scenario strict-mongo
```

Useful options:

```bash
uv run python benchmarks/profile_parse.py --iterations 500000 --limit 40
uv run python benchmarks/profile_parse.py --sort tottime
```

Common sort modes are:

- `cumtime`: time spent in a function and all functions it called
- `tottime`: time spent in the function body itself
- `calls` / `ncalls`: call-count oriented views

## Available scenarios

| Scenario | Measures |
| --- | --- |
| `strict-mongo` | Strict contract parse plus Mongo emission. |
| `strict-sql` | Strict contract parse plus SQL emission. |
| `loose-mongo` | Loose-mode parse plus Mongo emission. |
| `invalid-strict` | Strict-mode validation error path. |
| `emit-mongo` | Mongo emission from a prebuilt AST. |
| `emit-sql` | SQL emission from a prebuilt AST. |

The invalid path matters because malformed or hostile requests often exercise
validation and error construction more heavily than successful requests.

## Benchmarking rules

When optimizing Paramora:

1. Run the timing benchmark before the change.
2. Run the cProfile script to identify a real hotspot.
3. Make the smallest safe change.
4. Run tests, Ruff, and Pyright.
5. Run the same benchmark again.
6. Record before/after numbers in the PR description when the change is
   performance-motivated.

Recommended quality gate:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -vv
```

## Current pure-Python optimization strategy

The current Python implementation avoids repeated work in the request hot path:

- query contracts are compiled once when `Query(...)` is created
- field aliases, required fields, sortable fields, and allowed operators are reused
- scalar and list coercer functions are precomputed per field
- filter parameter splitting uses `str.rpartition("__")`
- Mongo and SQL emitters consume compiled contract metadata

This keeps installation simple while improving the common
`query.parse(...).output` path.

## Future Rust policy

Rust can be introduced later for hot loops only after profiling proves the need.
Rust-backed internals should preserve the Python API. If a Rust extension exposes
Python-callable objects, Paramora should ship `.pyi` stubs or typed Python
wrappers so Pyright, Pylance, and downstream users keep precise type information.

A Rust rewrite should not force a major version unless it changes user-facing
APIs, error shapes, AST contracts, or extension interfaces.

Potential future Rust boundaries:

- query parameter normalization
- filter parameter splitting
- scalar/list coercion
- AST construction for the successful fast path

Do not move backend emitters or extension interfaces to Rust until the Python API
and emitter contracts are stable.
