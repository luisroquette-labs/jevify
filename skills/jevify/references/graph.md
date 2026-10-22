# Build and read the graph

Use the Graphify version pinned by this skill. In a cloned Jevify checkout, run from the target repository:

```bash
env -u GEMINI_API_KEY -u GOOGLE_API_KEY -u OPENAI_API_KEY \
  -u ANTHROPIC_API_KEY -u OPENROUTER_API_KEY \
  GRAPHIFY_NO_AUTO_REFRESH=1 \
  uv run --project /path/to/jevify --frozen python -m graphify extract . --code-only
```

For a graph that already exists, use `update .` in place of `extract . --code-only`. Mixed code and semantic changes must use the installed Graphify skill's complete `--update` workflow, never a code-only shortcut. After Graphify finishes, run Jevify `finalize`; it verifies the manifest, report, visualization, and blocking integrity counts without repairing or rewriting the graph. Diagnose directly with `uv run --project /path/to/jevify --frozen python -m graphify diagnose multigraph --graph graphify-out/graph.json --json --max-examples 3`. Check graph size and warnings before accepting a refresh; investigate unexpected shrinkage.

For a direct read without memory, run `uv run --project /path/to/jevify --frozen python -m graphify query "question" --graph graphify-out/graph.json`. Graph edges are navigation evidence. Verify the source file and direction before stating a dependency, and verify runtime behavior separately.

When using only the copied `.skill` package, run the script once with `uv run /path/to/jevify/scripts/run.py --help` to install its pinned Graphify environment. The full project checkout is the supported path for build and diagnose commands.
