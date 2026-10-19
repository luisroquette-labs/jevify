---
name: jeviphy
description: Query a Graphify code graph with selected Claude Mem observations and optional Jev relevance decisions. Use when a user asks Claude Code or Codex to connect remembered project context to graph nodes, inspect that connection, or evaluate whether memory improves Graphify discovery.
---

# Jeviphy

Use Graphify's existing graph and query engine. Treat memory links as suggestions with source references, never as proven runtime dependencies.

## Default invocation

When the user invokes Jeviphy without an explicit question:

1. Generate three to five useful questions from the current graph, recent repository changes, and the user's active problem.
2. Rank them by user impact, operational risk, and how much the graph can clarify.
3. Select the highest-value question and run the baseline query automatically. Do not ask the user to choose a question first.
4. Check the selected result against the referenced source files before presenting conclusions. Separate graph suggestions, source-confirmed behavior, and runtime facts.

When the user supplies a question, use it directly. Question generation and baseline queries stay offline and require no paid API approval.

## Workflow

Install the skill for both supported hosts with:

```bash
python scripts/install_jeviphy_skill.py install --host both
```

Run `python skills/jeviphy/scripts/run.py doctor --repo PATH --graph PATH --corpus PATH`
before the first query. It checks the repository, graph commit, private corpus permissions, and
returns a single JSON diagnostic. `query` accepts the existing pilot arguments; `benchmark`
runs five or more paired offline retrieval passes for one frozen v2 case.

1. Locate the target Git repository and its `graphify-out/graph.json`. Confirm the graph's `built_at_commit` equals `git rev-parse HEAD`; use the [graph commands](references/graph.md) to build or refresh it offline when absent or stale.
2. Retrieve only the user's selected project observations through the supported Claude Mem bridge or another approved export. Keep the corpus outside Git, with mode `0700` on its directory and `0600` on files. Never read the Claude Mem database directly. Use the [memory workflow](references/memory.md) and [corpus schema](references/corpus.md).
3. Run the baseline query before any Jev decision. Example:

   ```bash
   uv run /path/to/jeviphy/skills/jeviphy/scripts/run.py \
     --repo /path/to/project --graph /path/to/project/graphify-out/graph.json \
     --corpus /private/path/corpus.json --case-id q001 --project project-name
   ```

4. For an offline relevance experiment, add `--decisions /private/path/decisions.json`. To test the bounded memory-aware candidate pool, add `--candidate-mode memory`. With reviewed `source_paths` on an observation, it keeps the question's first eight nodes and fills up to two slots with memory-scored nodes in those files. Without a scored node in those files, it uses the earlier seven-question/three-memory rule. The default `question` mode remains the comparison arm. For a local request preview, add `--dry-run`. Review its private payload before any external transmission.
   `--candidate-mode fast-source` is an optional offline experiment: it scores only nodes in cited source files, using the question and bounded memory summary in one pass, then uses the best three as Graphify traversal seeds. It can return fewer than ten nodes. Without cited paths and without a payload/decision request, it delegates directly to Graphify; unscored cited files and invalid Jev decisions use the unseeded answer path. Its three-repository stress result supports a conditional speed and precision gain for synthetic source-cited cases, not a general p95 or Jev-model gain; see `docs/jeviphy-fast-source-stress-20261018.md`.
5. Run `--live --approved-paid-use --max-requests 1` only after the user explicitly approves this paid API call and the exact class of code/memory content to send. Live Jev currently requires the user to have their own OpenRouter account and manually supply their own project-scoped key as `JEV_MEMORY_PILOT_API_KEY`; Jeviphy provides no hosted key or OAuth flow. Never auto-use a personal token or retry an uncertain call.

The runner caps work at ten nodes, three observations, thirty decisions, and a 24 KiB request. Missing or malformed decisions fall back to the unseeded Graphify query, including in memory candidate mode. Memory-aware query runs write `graphify-out/jev-memory-decisions.json`; no-source pass-through does not. Dry runs save a private payload outside Git. Neither mode alters the structural graph.

## Evaluate

Use human-labeled cases for paired ranking metrics. Report candidate recall, precision@5, recall@5, unsupported memory suggestions, latency, actual request count, and actual cost. An offline pass establishes technical behavior, not a Jev quality gain. Keep real observations, questions, and request previews out of commits and PRs.
