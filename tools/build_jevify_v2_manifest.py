"""Build the frozen Jevify cohort from a pinned SWE-bench Multilingual snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


GRAPHIFY_COMMIT = "4342e67107f77db54098d7873b563ff20830dcb8"
LANGUAGE_TARGETS = {
    "C": 14,
    "C++": 11,
    "Go": 14,
    "Java": 14,
    "JavaScript": 14,
    "TypeScript": 14,
    "PHP": 13,
    "Ruby": 13,
    "Rust": 13,
}
EXTENSIONS = {
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cxx": "C++",
    ".go": "Go",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".php": "PHP",
    ".rb": "Ruby",
    ".rs": "Rust",
}


def changed_files(patch: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(re.findall(r"^diff --git a/(.+?) b/", patch, re.MULTILINE)))


def language_for(row: dict) -> str | None:
    counts: Counter[str] = Counter()
    for filename in changed_files(row["patch"]):
        if row["repo"] in {"fmtlib/fmt", "nlohmann/json"} and filename.endswith((".h", ".hpp")):
            counts["C++"] += 1
            continue
        for extension, language in EXTENSIONS.items():
            if filename.endswith(extension):
                counts[language] += 1
                break
    return counts.most_common(1)[0][0] if counts else None


def stable_key(value: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()


def build_manifest(rows: list[dict], revision: str) -> dict:
    by_language: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if language := language_for(row):
            by_language[language].append(row)
    selected = []
    for language, count in LANGUAGE_TARGETS.items():
        candidates = sorted(
            by_language[language], key=lambda row: stable_key(row["instance_id"], "select")
        )
        if len(candidates) < count:
            raise ValueError(f"dataset has only {len(candidates)} {language} cases")
        selected.extend(candidates[:count])
    if len({row["instance_id"] for row in selected}) != 120:
        raise ValueError("selection must contain 120 unique cases")

    ordered = sorted(selected, key=lambda row: stable_key(row["instance_id"], "stratum"))
    strata = (
        ["valid_source"] * 40
        + ["stale_source"] * 20
        + ["no_source"] * 40
        + ["ambiguous"] * 20
    )
    stratum_by_id = {row["instance_id"]: stratum for row, stratum in zip(ordered, strata)}
    holdout_ids = {
        row["instance_id"]
        for row in sorted(selected, key=lambda row: stable_key(row["instance_id"], "holdout"))[:20]
    }

    repo_languages: dict[str, set[str]] = defaultdict(set)
    for row in selected:
        repo_languages[row["repo"]].add(language_for(row) or "Unknown")
    repos = [
        {
            "id": repo,
            "url": f"https://github.com/{repo}",
            "language": "/".join(sorted(languages)),
        }
        for repo, languages in sorted(repo_languages.items())
    ]

    cases = []
    for row in sorted(selected, key=lambda item: item["instance_id"]):
        stratum = stratum_by_id[row["instance_id"]]
        gold_files = changed_files(row["patch"])
        test_files = changed_files(row["test_patch"])
        if stratum in {"valid_source", "ambiguous"}:
            source_paths = list(gold_files)
            source_commit = row["base_commit"]
        elif stratum == "stale_source":
            source_paths = list(test_files or ("missing/removed-source",))
            source_commit = row["base_commit"]
        else:
            source_paths = []
            source_commit = None
        cases.append(
            {
                "id": row["instance_id"],
                "repo_id": row["repo"],
                "base_commit": row["base_commit"],
                "stratum": stratum,
                "question": row["problem_statement"],
                "timeout_seconds": 1800,
                "image": row["image"],
                "fail_to_pass": row["FAIL_TO_PASS"],
                "pass_to_pass": row["PASS_TO_PASS"],
                "gold_files": list(gold_files),
                "gold_symbols": [],
                "memory": {
                    "summary": (
                        "A prior review connected this behavior to the cited implementation paths."
                        if source_paths else ""
                    ),
                    "source_paths": source_paths,
                    "source_commit": source_commit,
                    "reviewed_at": "2026-10-19T00:00:00Z" if source_paths else None,
                },
                "holdout": row["instance_id"] in holdout_ids,
            }
        )
    return {
        "schema_version": 2,
        "graphify_commit": GRAPHIFY_COMMIT,
        "dataset_id": "SWE-bench/SWE-bench_Multilingual",
        "dataset_revision": revision,
        "repos": repos,
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, action="append", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for path in args.rows:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(item["row"] for item in payload["rows"])
    manifest = build_manifest(rows, args.revision)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
