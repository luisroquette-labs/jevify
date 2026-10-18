# Jeviphy code review — 2026-10-18

## Scope

The Jeviphy skill, its portable runner, the local memory pilot, the optional Jev API boundary, their tests, and the Jeviphy introduction in the README. The inherited Graphify engine is exercised by the repository test suite, but this review does not claim a line-by-line audit of upstream Graphify.

## Review and repair cycles

1. **Privacy and fallback:** malformed Jev choices now fail closed; live corpora require a private file and directory outside Git; decision sidecars are atomically written with mode `0600`, replacing any preexisting symlink without following it.
2. **Evaluation integrity:** duplicate candidate IDs, malformed suggestions, and duplicate suggestions can no longer distort reported ranking metrics.
3. **Portability and bounded I/O:** the installed skill is tested from an independent copy, source and skill copies are checked for parity, and Jev responses are limited to 1 MiB.
4. **Private previews:** dry-run output refuses a directory inside any Git worktree, including through a symlink. Tests no longer write previews to the user's home or rely on the process umask.
5. **HTTP and types:** the paid API client refuses redirects, keeping the project token on the configured endpoint. A response must identify the requested model or its hyphenated snapshot. The recall delta handles absent values explicitly.
6. **Inherited dependency and XML safety:** three vulnerable locked dependencies were upgraded; Maven POM parsing now rejects DTDs and entity expansion through `defusedxml`.
7. **Graphify security gate:** all project XML parsers now use `defusedxml`, including for UTF-16 input. Non-security SHA-1 uses are declared as such, wildcard bind addresses share a named constant, and Bandit plus `pip-audit` now block CI.

Each changed behavior has a focused regression test. No paid API call or real Claude Mem record was used during this review.

## Validation

- Pilot tests: 22 passed.
- Full repository suite with the `sql` extra: 8,234 passed, 150 skipped after the dependency and XML fixes. The first run without the optional SQL parser had seven dependency-related failures; the same area passed after installing that extra. The sidecar symlink regression was added after this full run; its focused suite passed 88 tests.
- Ruff on changed Python files, Pyright on the Jeviphy files and manifest parser, Bandit, and five Graphify skill-generation checks passed after their respective fixes. A wider Pyright probe of inherited Graphify modules produced 72 errors from missing optional imports and existing types; those modules are covered by the repository tests, but this review does not claim project-wide type cleanliness.
- `pip-audit --strict` found no known vulnerabilities after the bounded lockfile upgrade. Bandit passed without findings or stale `nosec` warnings.

## Release boundary

This review proves the local implementation and offline fallback behavior. It does not establish a retrieval gain from Jev on real memory. A real paired evaluation, exact outbound payload review, and explicit approval for paid API use remain separate gates before any performance claim.
