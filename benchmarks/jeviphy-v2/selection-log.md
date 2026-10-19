# Jeviphy v2 cohort selection

- Source: [`SWE-bench/SWE-bench_Multilingual`](https://huggingface.co/datasets/SWE-bench/SWE-bench_Multilingual)
- Dataset revision: `846e647b9f33c0b51b739d005d13d85493c9af09`
- Graphify revision: `4342e67107f77db54098d7873b563ff20830dcb8`
- Selection date: 2026-10-19
- License of the dataset: MIT

The builder reads all 300 official rows, identifies language from the solution patch, and selects 120 cases by a salted SHA-256 ordering. The result spans 38 repositories and nine languages. Another salted ordering assigns exactly 20 holdout cases. A third ordering assigns the predeclared 40 valid-source, 20 stale-source, 40 no-source, and 20 ambiguous strata.

Valid and ambiguous source evidence uses implementation paths from the official solution patch. Stale-source evidence uses paths from the official test patch, which should be absent or non-implementation evidence at the base commit. No-source controls contain no paths. The issue text is preserved verbatim from SWE-bench, and the memory summary adds no solution symbol or implementation detail.

Regenerate from three 100-row Dataset Viewer API snapshots with:

```bash
uv run --frozen python -m tools.build_jeviphy_v2_manifest \
  --rows /tmp/swebench-multilingual-0.json \
  --rows /tmp/swebench-multilingual-100.json \
  --rows /tmp/swebench-multilingual-200.json \
  --revision 846e647b9f33c0b51b739d005d13d85493c9af09 \
  --output benchmarks/jeviphy-v2/manifest.json
```

The checked-in `MANIFEST.sha256` is the freeze receipt. Any content change requires a new benchmark version.
