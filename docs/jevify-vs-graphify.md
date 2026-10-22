# Jevify and Graphify: scope and latency

## Short answer

Graphify is the complete graph engine. It extracts repository structure, writes
the graph, builds communities and answers broad graph queries. Jevify is a
bounded workflow on top of Graphify. It reuses the existing graph and can start
from reviewed source paths instead of searching the whole graph.

That narrower path can feel much quicker, but JEV is not the reason. The default
Jevify workflow makes no JEV request. In the paid 19-call pilot, JEV added
649.74 ms p50 and 1,083.09 ms p95 of API latency, with no change in top-five
hits.

## What each timing includes

| Operation | Work performed |
| --- | --- |
| `graphify update .` | Parse changed files, resolve graph edges, update communities and write artifacts. |
| `graphify query` | Load the current graph and run an unseeded structural query. |
| `$jevify` without reviewed sources | Validate the graph and delegate to the same Graphify query path. |
| `$jevify` with valid `source_paths` | Score nodes from cited files, choose up to three seeds and ask Graphify for a bounded traversal. |
| Jevify with live JEV | Add a remote relevance decision before the bounded Graphify query. |

Comparing a Graphify rebuild with a Jevify query compares different operations.
On the same current graph and without source hints, Jevify should stay close to
Graphify plus wrapper overhead. The frozen zero-configuration evaluation measured
4.56% median and 9.26% p95 matched-pair overhead for that wrapper.

## Where the large differences came from

The historical v2 experiment reported a 4,170.41 ms Graphify p95 and a 170.47 ms
Jevify p95 on valid source cases. That ratio is about 24.5x, but it measured a
narrow source-cited retrieval path against an unseeded whole-graph query. It did
not measure general repository understanding, graph construction, end-to-end
agent work or a JEV-model benefit.

A later synthetic COESA cohort measured source-backed p50/p95 of 161.88/200.46 ms
for Graphify and 43.55/69.87 ms for Jevify. The pooled tail result varied across
repositories and repeat runs, so the evidence does not support a universal speed
claim.

## Practical interpretation

- Use Graphify when the graph is missing or stale, or when the question needs
  broad structural discovery.
- Use Jevify when a current graph already exists and reviewed memory cites likely
  source files.
- Treat a large latency gap as a signal to check whether one path rebuilt or
  searched the entire graph while the other reused it with valid seeds.
- Verify cited source before accepting the narrower answer. Relevant code outside
  the cited files can still matter.

## Name migration boundary

Jevify is the canonical product, command, skill and URL. Frozen v1 evidence keeps
the former `jeviphy` field names inside immutable JSON and checksum files. Those
legacy schema strings describe historical receipts and are not active routes.
