# Profiling and future Rust hotspots

Paramora should stay Python-only while the public API, AST, error model, and
extension model are still moving. Performance work should be evidence-driven.

## Current profiling tool

A small cProfile harness exists at `benchmarks/profile_parse.py`:

```bash
uv run python benchmarks/profile_parse.py
```

Use this before and after parser/emitter changes to identify real bottlenecks.

## Future Rust policy

Rust can be introduced later for hot loops only after profiling proves the need.
Rust-backed internals should preserve the Python API. If a Rust extension exposes
Python-callable objects, ship `.pyi` stubs or typed Python wrappers so Pyright,
Pylance, and downstream users keep precise type information.

A Rust rewrite should not force a major version unless it changes user-facing
APIs, error shapes, AST contracts, or extension interfaces.
