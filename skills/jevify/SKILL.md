---
name: jevify
description: Query a Graphify code graph with selected Claude Mem observations and optional Jev relevance decisions. Use when a user asks Claude Code or Codex to connect remembered project context to graph nodes, inspect that connection, or evaluate whether memory improves Graphify discovery.
---

# Jevify

Use Graphify's existing graph and query engine. Treat memory links as suggestions with source references, never as proven runtime dependencies.

## Default invocation

Resolve the directory containing this installed `SKILL.md` as `JEVIFY_SKILL_DIR`. Preserve the
target repository as the process working directory, then run:

```bash
uv run "$JEVIFY_SKILL_DIR/scripts/run.py" auto
```

Pass an explicit question as `auto --question "..."`.
Do not reproduce auto discovery in the host prompt: the runner resolves the Git root, repairs the graph once when needed, selects a useful
question, and completes the offline Graphify query. Do not ask the user to choose a repository,
question, corpus, mode, or credential. Check cited source files before presenting conclusions.

A corpus is optional. When reviewed observations are already available through `memory-gateway`,
write the single-case corpus outside Git with directory mode `0700` and file mode `0600`, then rerun
the same command with `--corpus PATH`. Without it, finish with the graph-only answer.

## Workflow

Install the skill for both supported hosts with:

```bash
python scripts/install_jevify_skill.py install --host both
```

Run `uv run "$JEVIFY_SKILL_DIR/scripts/run.py" doctor` for a read-only diagnostic when needed.
It checks the current repository and graph; add `--corpus PATH` to check private corpus permissions.
`query` accepts the existing strict pilot arguments; `benchmark`
runs five or more paired offline retrieval passes for one frozen v2 case.

1. Use `auto`; repository discovery, graph validation, and one bounded repair belong to the runner.
2. When approved project observations are available, retrieve only the relevant ones through the supported Claude Mem bridge or another approved export. Keep the corpus outside Git, with mode `0700` on its directory and `0600` on files. Never read the Claude Mem database directly. Use the [memory workflow](references/memory.md) and [corpus schema](references/corpus.md). Otherwise continue with the graph-only baseline.
3. Use the strict legacy interface only for an explicit evaluation. Example:

   ```bash
   uv run "$JEVIFY_SKILL_DIR/scripts/run.py" query \
     --repo /path/to/project --graph /path/to/project/graphify-out/graph.json \
     --corpus /private/path/corpus.json --case-id q001 --project project-name
   ```

4. For an offline relevance experiment, add `--decisions /private/path/decisions.json`. To test the bounded memory-aware candidate pool, add `--candidate-mode memory`. With reviewed `source_paths` on an observation, it keeps the question's first eight nodes and fills up to two slots with memory-scored nodes in those files. Without a scored node in those files, it uses the earlier seven-question/three-memory rule. The default `question` mode remains the comparison arm. For a local request preview, add `--dry-run`. Review its private payload before any external transmission.
   `--candidate-mode fast-source` is an optional offline experiment: it scores only nodes in cited source files, using the question and bounded memory summary in one pass, then uses the best three as Graphify traversal seeds. It can return fewer than ten nodes. Without cited paths and without a payload/decision request, it delegates directly to Graphify; unscored cited files and invalid Jev decisions use the unseeded answer path. Its three-repository stress result supports a conditional speed and precision gain for synthetic source-cited cases, not a general p95 or Jev-model gain; see `docs/jevify-fast-source-stress-20261018.md`.
5. Run `--live --approved-paid-use --max-requests 1` only after the user explicitly approves paid Jev calls and the exact class of code/memory content to send. That approval persists for the current conversation within its approved provider, project, content, request, and cost limits: continue automatically without asking again or offering offline/live choices after every step. Ask again only before exceeding the approved scope. Live Jev currently requires the user to have their own OpenRouter account and manually supply their own project-scoped key as `JEV_MEMORY_PILOT_API_KEY`; Jevify provides no hosted key or OAuth flow. If the key is missing, rejected, or expired, or the request outcome is uncertain, accept the runner's baseline fallback, mention the skipped live enrichment in one sentence, and finish the source-verified answer. Do not stop the invocation to request a new key. Never auto-use a personal token or retry an uncertain call.

The runner caps work at ten nodes, three observations, thirty decisions, and a 24 KiB request. Missing or malformed decisions fall back to the unseeded Graphify query, including in memory candidate mode. Memory-aware query runs write `graphify-out/jev-memory-decisions.json`; no-source pass-through does not. Dry runs save a private payload outside Git. Neither mode alters the structural graph.

## Evaluate

Use human-labeled cases for paired ranking metrics. Report candidate recall, precision@5, recall@5, unsupported memory suggestions, latency, actual request count, and actual cost. An offline pass establishes technical behavior, not a Jev quality gain. Keep real observations, questions, and request previews out of commits and PRs.
