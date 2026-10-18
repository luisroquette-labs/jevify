---
name: jeviphy
description: Query a Graphify code graph with selected Claude Mem observations and optional Jev relevance decisions. Use when a user asks Claude Code or Codex to connect remembered project context to graph nodes, inspect that connection, or evaluate whether memory improves Graphify discovery.
---

# Jeviphy

Use Graphify's existing graph and query engine. Treat memory links as suggestions with source references, never as proven runtime dependencies.

## Workflow

1. Locate the target Git repository and its `graphify-out/graph.json`. Confirm the graph's `built_at_commit` equals `git rev-parse HEAD`; use the [graph commands](references/graph.md) to build or refresh it offline when absent or stale.
2. Retrieve only the user's selected project observations through the supported Claude Mem bridge or another approved export. Keep the corpus outside Git, with mode `0700` on its directory and `0600` on files. Never read the Claude Mem database directly. Use the [memory workflow](references/memory.md) and [corpus schema](references/corpus.md).
3. Run the baseline query before any Jev decision. Example:

   ```bash
   uv run /path/to/jeviphy/skills/jeviphy/scripts/run.py \
     --repo /path/to/project --graph /path/to/project/graphify-out/graph.json \
     --corpus /private/path/corpus.json --case-id q001 --project project-name
   ```

4. For an offline relevance experiment, add `--decisions /private/path/decisions.json`. For a local request preview, add `--dry-run`. Review its private payload before any external transmission.
5. Run `--live --approved-paid-use --max-requests 1` only after the user explicitly approves this paid API call and the exact class of code/memory content to send. Supply a project-scoped `JEV_MEMORY_PILOT_API_KEY` manually. Never auto-use a personal token or retry an uncertain call.

The runner caps work at ten nodes, three observations, thirty decisions, and a 24 KiB request. Missing or malformed decisions fall back to the unseeded Graphify query. It writes only `graphify-out/jev-memory-decisions.json`; it does not alter the structural graph.

## Evaluate

Use human-labeled cases for paired ranking metrics. Report candidate recall, precision@5, recall@5, unsupported memory suggestions, latency, actual request count, and actual cost. An offline pass establishes technical behavior, not a Jev quality gain. Keep real observations, questions, and request previews out of commits and PRs.
