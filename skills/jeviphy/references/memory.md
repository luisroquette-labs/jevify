# Memory selection

Use `memory-gateway` MCP when available. Search within the chosen project, inspect only the observations needed for the question, and retain each observation's ID and source reference. If the gateway is unavailable, use an explicitly approved export; do not read `claude-mem` SQLite files directly.

Review and shorten each summary before placing it in the local corpus. Keep at most three observations per question and remove secrets, personal information, and irrelevant details. Store real corpora and request previews outside all Git worktrees. Validate directory mode `0700` and file mode `0600` before a live request.

The runner's offline mode never reads a provider key. A dry run creates the exact request body locally for human review. A live request may transmit the question, up to ten committed code excerpts, and up to three shortened summaries; obtain explicit approval for this content and paid API use first.
