"""Run a small, fully synthetic Jevify demo without network model calls."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.jev_memory_pilot import apply_decisions, candidate_pool


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="jevify-demo-") as directory:
        root = Path(directory)
        repo = root / "repo"
        repo.mkdir()
        (repo / "auth.py").write_text(
            '"""Public code and memory demo."""\n\n'
            'def validate_token(token: str) -> bool:\n'
            '    return token.startswith("demo-")\n\n'
            'def authorize(token: str) -> bool:\n'
            '    return validate_token(token)\n', encoding="utf-8",
        )
        (repo / "billing.py").write_text(
            '"""Unrelated code in the same project."""\n\n'
            'def charge_invoice(invoice_id: str) -> str:\n'
            '    return f"charged:{invoice_id}"\n', encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "add", "auth.py", "billing.py"], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "-c", "user.name=Jevify",
             "-c", "user.email=demo@example.invalid", "-c", "commit.gpgsign=false",
             "-c", "core.hooksPath=/dev/null", "commit", "-qm", "Public demo"],
            check=True,
        )

        env = {key: value for key, value in os.environ.items()
               if key not in {"GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY",
                              "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY",
                              "MOONSHOT_API_KEY", "DEEPSEEK_API_KEY",
                              "JEV_MEMORY_PILOT_API_KEY"}}
        env["GRAPHIFY_NO_AUTO_REFRESH"] = "1"
        subprocess.run(
            [sys.executable, "-m", "graphify", "extract", str(repo), "--code-only"],
            check=True, capture_output=True, text=True, env=env,
        )
        graph = repo / "graphify-out" / "graph.json"
        before = hashlib.sha256(graph.read_bytes()).hexdigest()
        question = "auth token"
        candidates = candidate_pool(graph, repo, question)
        target = "auth_validate_token"
        target_candidate = next(item for item in candidates if item["node_id"] == target)
        baseline_rank = target_candidate["baseline_rank"]
        assert target_candidate["source_file"] == "auth.py"
        assert baseline_rank > 1, "demo must show a visible ranking change"

        private = root / "private"
        private.mkdir(mode=0o700)
        observation_id = "synthetic-001"
        corpus = {
            "observations": [{"id": observation_id, "project": "public-demo",
                              "date": "2026-10-18",
                              "summary": "validate_token checks the token prefix before authorize returns access.",
                              "source_ref": "public-synthetic-observation"}],
            "cases": [{"id": "demo-001", "question": question,
                       "relevant_node_ids": [target],
                       "relevant_pairs": [[target, observation_id]],
                       "observation_ids": [observation_id]}],
        }
        corpus_path = private / "corpus.json"
        corpus_path.write_text(json.dumps(corpus), encoding="utf-8")
        corpus_path.chmod(0o600)
        decisions = {
            "decisions": [{"node_id": item["node_id"], "observation_id": observation_id,
                           "choice": "relevant" if item["node_id"] == target else "unrelated",
                           "probability": 0.99} for item in candidates]
        }
        decision_path = private / "decisions.json"
        decision_path.write_text(json.dumps(decisions), encoding="utf-8")
        decision_path.chmod(0o600)

        args = [sys.executable, "-m", "tools.jev_memory_pilot", "--repo", str(repo),
                "--graph", str(graph), "--corpus", str(corpus_path),
                "--case-id", "demo-001", "--project", "public-demo"]
        baseline = subprocess.run(args, check=True, capture_output=True, text=True, env=env)
        assisted = subprocess.run(
            [*args, "--decisions", str(decision_path)],
            check=True, capture_output=True, text=True, env=env,
        )
        answers = {(item["node_id"], observation_id):
                   {"choice": item["choice"], "probability": item["probability"]}
                   for item in decisions["decisions"]}
        ordered, suggestions = apply_decisions(
            candidates, corpus["observations"], answers,
            eligible_node_ids={item["node_id"] for item in candidates}, threshold=0.8,
        )
        assert ordered[0]["node_id"] == target and len(suggestions) == 1
        assert "Suggested memory link:" not in baseline.stdout
        assert f"Suggested memory link: {target}" in assisted.stdout
        assert hashlib.sha256(graph.read_bytes()).hexdigest() == before
        location = f"{target_candidate['source_file']}:{target_candidate['source_location']}"
        print(f"Graphify baseline: {target} at rank {baseline_rank}")
        print(f"Synthetic offline decision: {target} at rank 1")
        print(f"Evidence: {target} at {location} ↔ {observation_id}")
        print("Graph unchanged; Jev API calls: 0")


if __name__ == "__main__":
    main()
