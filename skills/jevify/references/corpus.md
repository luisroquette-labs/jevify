# Local corpus format

```json
{
  "observations": [{
    "id": "synthetic-001",
    "project": "project-name",
    "date": "2026-10-17",
    "summary": "A short, reviewed observation.",
    "source_ref": "memory-reference",
    "source_paths": ["src/handler.py"]
  }],
  "cases": [{
    "id": "q001",
    "question": "Where is the handler?",
    "relevant_node_ids": ["src/handler.py::handle"],
    "relevant_pairs": [["src/handler.py::handle", "synthetic-001"]],
    "observation_ids": ["synthetic-001"]
  }]
}
```

`relevant_node_ids` and `relevant_pairs` are human labels for evaluation, not Jev output. Use an empty list when no node or pair is relevant. Every node ID must exist in the pinned graph. At most three observations may be selected for one case.

`source_paths` is optional. Populate it only with reviewed, repo-relative implementation file paths cited by the selected memory; the supported memory gateway's `files_modified` field can provide candidates for review. Paths are local retrieval hints, never proof that the current code still behaves as remembered. The `source_paths` field is not sent to Jev; selected node IDs and excerpts still require payload review.

Offline decisions use `{"decisions":[{"node_id":"...","observation_id":"...","choice":"relevant","probability":0.9}]}`. Provide one entry for every eligible node-observation pair; an incomplete set causes baseline fallback. Choices are `relevant`, `unrelated`, or `insufficient_evidence`.
