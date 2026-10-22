import json
import os
import subprocess
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import networkx as nx
import pytest
from networkx.readwrite import json_graph

from graphify.detect import save_manifest
from skills.jevify.scripts.run import doctor
from tools import jevify_autorun as autorun
from tools import jevify_graph_state as graph_state
from tools.jevify_autorun import ContextError, auto, ensure_context, inspect_context, select_question
from tools.jevify_graph_state import inspect_graph_freshness


def _commit(repo: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def _git_status(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "status", "--short"], cwd=repo, text=True,
    )


def _write_graph(path: Path, commit: object) -> None:
    graph = nx.Graph()
    graph.add_node("app.py::run", label="run", type="function", community=0,
                   source_file="app.py", source_location="L1")
    data = json_graph.node_link_data(graph, edges="links")
    if commit is not ...:
        data["built_at_commit"] = commit
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def write_graphify_manifest(repo: Path) -> Path:
    path = repo / "graphify-out" / "manifest.json"
    save_manifest(
        {"code": [str(repo / "app.py")]},
        manifest_path=str(path),
        kind="both",
        root=repo,
    )
    return path


@pytest.fixture
def repo_with_graph(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo with spaces"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "app.py").write_text("def run(): return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c",
                    "user.email=test@example.invalid", "commit", "-qm", "fixture"],
                   cwd=repo, check=True)
    graph = repo / "graphify-out" / "graph.json"
    _write_graph(graph, _commit(repo))
    write_graphify_manifest(repo)
    return repo, graph


def test_same_head_with_modified_code_is_stale(repo_with_graph):
    repo, _ = repo_with_graph
    (repo / "app.py").write_text("def run(): return 2\n", encoding="utf-8")

    state = inspect_context(repo)

    assert state.status == "stale"
    assert state.freshness.changed_by_type == (("code", 1),)
    assert state.freshness.deleted == 0


def test_same_head_with_new_document_is_stale(repo_with_graph):
    repo, _ = repo_with_graph
    (repo / "DECISION.md").write_text("# Decision\n", encoding="utf-8")

    state = inspect_context(repo)

    assert state.status == "stale"
    assert state.freshness.requires_semantic_host is True


def test_same_head_with_deleted_file_is_stale(repo_with_graph):
    repo, _ = repo_with_graph
    (repo / "app.py").unlink()

    freshness = inspect_context(repo).freshness

    assert freshness.deleted == 1
    assert freshness.deleted_by_type == (("code", 1),)


def test_doctor_freshness_scan_does_not_mutate_repo(repo_with_graph, capsys):
    repo, graph = repo_with_graph
    manifest = repo / "graphify-out" / "manifest.json"
    before = {path: path.read_bytes() for path in (graph, manifest)}
    status_before = _git_status(repo)

    assert doctor(["--repo", str(repo)]) == 0

    assert json.loads(capsys.readouterr().out)["freshness"]["status"] == "current"
    assert {path: path.read_bytes() for path in (graph, manifest)} == before
    assert _git_status(repo) == status_before


def test_freshness_surfaces_sensitive_skip(repo_with_graph, monkeypatch):
    repo, graph = repo_with_graph
    monkeypatch.setattr(graph_state, "detect_incremental", lambda *_a, **_k: {
        "new_files": {},
        "deleted_files": [],
        "skipped_sensitive": [".env.production"],
    })

    result = inspect_graph_freshness(repo, graph)

    assert result.skipped_sensitive == (".env.production",)


def test_malformed_manifest_is_unavailable_not_current(repo_with_graph):
    repo, graph = repo_with_graph
    (graph.parent / "manifest.json").write_text("{", encoding="utf-8")

    assert inspect_graph_freshness(repo, graph).status == "unavailable"


def test_ensure_context_uses_containing_git_root(repo_with_graph):
    repo, graph = repo_with_graph
    nested = repo / "src" / "nested"
    nested.mkdir(parents=True)
    context = ensure_context(nested)
    assert context.repo == repo.resolve()
    assert context.graph == graph.resolve()


def test_ensure_context_rejects_outside_git(tmp_path):
    with pytest.raises(ContextError, match="not inside a Git worktree"):
        ensure_context(tmp_path)


def test_explicit_repository_and_graph_are_resolved(repo_with_graph, tmp_path):
    repo, graph = repo_with_graph
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    assert ensure_context(elsewhere, repo=repo).graph == graph.resolve()
    assert ensure_context(elsewhere, repo=repo, graph=graph).repo == repo.resolve()


def test_persisted_commit_is_normalized_and_accepted(repo_with_graph):
    repo, _ = repo_with_graph
    state = inspect_context(repo)
    assert state.status == "ready"
    assert state.loaded_graph.graph["_built_at_commit"] == state.context.head


@pytest.mark.parametrize("value", [..., None, "", 42])
def test_missing_or_malformed_persisted_commit_is_stale(repo_with_graph, value):
    repo, graph = repo_with_graph
    _write_graph(graph, value)
    assert inspect_context(repo).status == "stale"


@pytest.mark.parametrize(
    ("initial", "expected"),
    [("missing", ["extract", ".", "--code-only"]),
     ("corrupt", ["extract", ".", "--force", "--code-only"]),
     ("stale", ["update", "."])],
)
def test_repair_runs_once_without_provider_credentials(
    repo_with_graph, monkeypatch, initial, expected,
):
    repo, graph = repo_with_graph
    if initial == "missing":
        graph.unlink()
    elif initial == "corrupt":
        graph.write_text("{", encoding="utf-8")
    else:
        _write_graph(graph, "0" * 40)
    calls = []

    def fake_run(command, repo_arg, env):
        calls.append((command, repo_arg, env))
        _write_graph(graph, _commit(repo))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(autorun, "_run_repair", fake_run)
    for key in autorun.PROVIDER_ENV_KEYS:
        monkeypatch.setenv(key, "secret-sentinel")
    context = ensure_context(repo)
    assert context.head == _commit(repo)
    assert len(calls) == 1
    command, repo_arg, env = calls[0]
    assert command == [sys.executable, "-m", "graphify", *expected]
    assert repo_arg == repo.resolve()
    assert env["GRAPHIFY_NO_AUTO_REFRESH"] == "1"
    assert env["PYTHONHASHSEED"] == "0"
    assert not (set(autorun.PROVIDER_ENV_KEYS) & set(env))


def test_failed_repair_does_not_retry(repo_with_graph, monkeypatch):
    repo, graph = repo_with_graph
    graph.unlink()
    calls = []

    def fail(command, repo_arg, env):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, "", "bounded failure")

    monkeypatch.setattr(autorun, "_run_repair", fail)
    with pytest.raises(ContextError, match="graph repair failed.*bounded failure"):
        ensure_context(repo)
    assert len(calls) == 1


def test_failed_corrupt_repair_restores_original(repo_with_graph, monkeypatch):
    repo, graph = repo_with_graph
    graph.write_text("{broken", encoding="utf-8")

    monkeypatch.setattr(
        autorun, "_run_repair",
        lambda command, repo_arg, env: subprocess.CompletedProcess(
            command, 1, "", "bounded failure",
        ),
    )
    with pytest.raises(ContextError, match="graph repair failed"):
        ensure_context(repo)
    assert graph.read_text(encoding="utf-8") == "{broken"
    assert not list(graph.parent.glob(".graph.json.jevify-corrupt-*"))


def test_invalid_repaired_graph_is_rejected_without_retry(repo_with_graph, monkeypatch):
    repo, graph = repo_with_graph
    graph.unlink()
    calls = []

    def no_output(command, repo_arg, env):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(autorun, "_run_repair", no_output)
    with pytest.raises(ContextError, match="repair produced invalid graph"):
        ensure_context(repo)
    assert len(calls) == 1


def test_corrupt_graph_real_force_rebuild(repo_with_graph):
    repo, graph = repo_with_graph
    graph.write_text("{", encoding="utf-8")
    context = ensure_context(repo)
    assert context.graph == graph.resolve()
    assert inspect_context(repo).status == "ready"


def test_explicit_question_wins(repo_with_graph, monkeypatch):
    _, graph_path = repo_with_graph
    graph = autorun._read_graph(str(graph_path))
    monkeypatch.setattr(autorun, "suggest_questions", lambda *args, **kwargs: pytest.fail())
    assert select_question(graph, graph_path, " What calls run? ") == "What calls run?"


def test_first_high_confidence_suggestion_wins(repo_with_graph, monkeypatch):
    _, graph_path = repo_with_graph
    graph = autorun._read_graph(str(graph_path))
    monkeypatch.setattr(autorun, "suggest_questions", lambda *args, **kwargs: [
        {"question": "low", "low_confidence": True},
        {"question": "selected", "low_confidence": False},
        {"question": "later", "low_confidence": False},
    ])
    assert select_question(graph, graph_path, None) == "selected"


@pytest.mark.parametrize("question", [None, "", "   "])
def test_selection_falls_back_to_first_low_confidence(repo_with_graph, monkeypatch, question):
    _, graph_path = repo_with_graph
    graph = autorun._read_graph(str(graph_path))
    monkeypatch.setattr(autorun, "suggest_questions", lambda *args, **kwargs: [
        {"question": "low", "low_confidence": True},
    ])
    assert select_question(graph, graph_path, question) == "low"


@pytest.mark.parametrize("suggestions", [[], [{"type": "no_signal"}], [{"question": ""}]])
def test_selection_rejects_graph_without_question_signal(
    repo_with_graph, monkeypatch, suggestions,
):
    _, graph_path = repo_with_graph
    graph = autorun._read_graph(str(graph_path))
    monkeypatch.setattr(autorun, "suggest_questions", lambda *args, **kwargs: suggestions)
    with pytest.raises(ContextError, match="graph has no question signal"):
        select_question(graph, graph_path, None)


def test_labels_use_valid_file_or_community_fallback(repo_with_graph, monkeypatch):
    _, graph_path = repo_with_graph
    graph = autorun._read_graph(str(graph_path))
    seen = []
    monkeypatch.setattr(autorun, "suggest_questions", lambda _g, _c, labels, **_k: (
        seen.append(labels) or [{"question": "selected"}]
    ))
    select_question(graph, graph_path, None)
    (graph_path.parent / ".graphify_labels.json").write_text('{"0":"Runtime"}')
    select_question(graph, graph_path, None)
    assert seen == [{0: "Community 0"}, {0: "Runtime"}]


def test_question_selection_is_stable_across_hash_seeds(repo_with_graph):
    repo, graph_path = repo_with_graph
    graph = nx.Graph()
    for index in range(3):
        graph.add_node(f"n{index}", label=f"node{index}", type="function", community=index % 2,
                       source_file="app.py", source_location="L1")
    graph.add_edges_from([("n0", "n1"), ("n1", "n2")])
    data = json_graph.node_link_data(graph, edges="links")
    data["built_at_commit"] = _commit(repo)
    graph_path.write_text(json.dumps(data), encoding="utf-8")
    code = (
        "from pathlib import Path; from graphify.serve import _read_graph; "
        "from tools.jevify_autorun import select_question; "
        f"p=Path({str(graph_path)!r}); print(select_question(_read_graph(str(p)), p, None))"
    )
    outputs = {
        subprocess.check_output(
            [sys.executable, "-c", code], text=True,
            env={**os.environ, "PYTHONHASHSEED": str(seed)},
        ).strip()
        for seed in range(20)
    }
    assert len(outputs) == 1


def test_bare_auto_uses_current_repo_without_provider_key(
    repo_with_graph, monkeypatch, capsys,
):
    repo, graph_path = repo_with_graph
    (repo / "src").mkdir()
    monkeypatch.setattr(autorun, "select_question", lambda *_args: "Where is run?")
    monkeypatch.setattr(
        autorun, "query_graphify_exact",
        lambda _loaded, graph, question: f"answer:{graph.name}:{question}\n",
    )
    real_get = os.environ.get

    def guarded_get(key, default=None):
        if key == "JEV_MEMORY_PILOT_API_KEY":
            raise AssertionError("default auto read provider key")
        return real_get(key, default)

    monkeypatch.setattr(os.environ, "get", guarded_get)
    assert auto([], repo / "src") == 0
    captured = capsys.readouterr()
    assert captured.out == "Question: Where is run?\nanswer:graph.json:Where is run?\n"
    assert captured.err == ""
    assert graph_path.is_file()


def test_auto_json_has_stable_envelope(repo_with_graph, monkeypatch, capsys):
    repo, _ = repo_with_graph
    monkeypatch.setattr(autorun, "query_graphify_exact",
                        lambda *_args: "exact answer\n")
    assert auto(["--question", "What calls run?", "--json"], repo) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "answer": "exact answer\n",
        "graph": str((repo / "graphify-out/graph.json").resolve()),
        "live_enrichment": "not_requested",
        "mode": "graph_only",
        "question": "What calls run?",
        "repo": str(repo.resolve()),
        "schema_version": 1,
    }


def test_in_process_graph_query_matches_direct_graphify(repo_with_graph):
    _, graph_path = repo_with_graph
    graph = autorun._read_graph(str(graph_path))
    expected = subprocess.run(
        [sys.executable, "-m", "graphify", "query", "run", "--graph", str(graph_path)],
        capture_output=True, text=True, check=True,
        env={**os.environ, "GRAPHIFY_QUERY_LOG_DISABLE": "1"},
    ).stdout
    assert autorun.query_graphify_exact(graph, graph_path, "run") == expected


def test_ambiguous_or_mismatched_corpus_falls_back_once(
    repo_with_graph, tmp_path, monkeypatch, capsys,
):
    repo, _ = repo_with_graph
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({"observations": [], "cases": [
        {"id": "one", "question": "one"}, {"id": "two", "question": "two"},
    ]}))
    monkeypatch.setattr(autorun, "query_graphify_exact",
                        lambda *_args: "fallback\n")
    assert auto(["--question", "explicit", "--corpus", str(corpus)], repo) == 0
    captured = capsys.readouterr()
    assert captured.out.endswith("fallback\n")
    assert captured.err == "memory_enrichment=skipped\n"


def test_single_case_corpus_supplies_question_and_memory_mode(
    repo_with_graph, tmp_path, monkeypatch, capsys,
):
    repo, _ = repo_with_graph
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({
        "observations": [{"id": "o1", "project": "demo"}],
        "cases": [{"id": "q1", "question": "Where is run?", "observation_ids": ["o1"]}],
    }))
    seen = []

    def pilot(config):
        seen.append(config)
        return SimpleNamespace(answer="seeded\n", live_enrichment="not_requested",
                               actual_cost=None, memory_applied=True)

    monkeypatch.setattr("tools.jev_memory_pilot.run_pilot", pilot)
    assert auto(["--corpus", str(corpus), "--json"], repo) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["question"] == "Where is run?"
    assert payload["mode"] == "memory_offline"
    assert seen[0].candidate_mode == "fast-source"


def test_live_without_corpus_skips_without_key_read(repo_with_graph, monkeypatch, capsys):
    repo, _ = repo_with_graph
    monkeypatch.setattr(autorun, "query_graphify_exact",
                        lambda *_args: "offline\n")
    real_get = os.environ.get

    def guarded_get(key, default=None):
        if key == "JEV_MEMORY_PILOT_API_KEY":
            raise AssertionError("live without corpus read provider key")
        return real_get(key, default)

    monkeypatch.setattr(os.environ, "get", guarded_get)
    assert auto(["--question", "Where?", "--live", "--approved-paid-use",
                 "--max-requests", "1"], repo) == 0
    captured = capsys.readouterr()
    assert captured.out.endswith("offline\n")
    assert captured.err == "live_enrichment=skipped\n"


def _private_corpus(tmp_path: Path) -> Path:
    tmp_path.chmod(0o700)
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({
        "observations": [{"id": "o1", "project": "demo", "date": "2026-10-19",
                          "summary": "run is implemented in app.py", "source_ref": "reviewed-o1",
                          "source_paths": ["app.py"]}],
        "cases": [{"id": "q1", "question": "Where is run?",
                   "relevant_node_ids": ["app.py::run"],
                   "relevant_pairs": [["app.py::run", "o1"]],
                   "observation_ids": ["o1"]}],
    }))
    corpus.chmod(0o600)
    return corpus


@pytest.mark.parametrize("failure", [
    TimeoutError(),
    urllib.error.HTTPError("https://example.invalid", 401, "expired", {}, None),
    urllib.error.HTTPError("https://example.invalid", 429, "limited", {}, None),
    urllib.error.HTTPError("https://example.invalid", 302, "redirect blocked", {}, None),
    ValueError("malformed response"),
    ValueError("Jev response exceeds 1 MiB"),
])
def test_live_failure_returns_offline_answer_once(
    repo_with_graph, tmp_path, monkeypatch, capsys, failure,
):
    from unittest.mock import patch

    repo, _ = repo_with_graph
    corpus = _private_corpus(tmp_path)
    assert auto(["--corpus", str(corpus), "--json"], repo) == 0
    offline = json.loads(capsys.readouterr().out)["answer"]
    monkeypatch.setenv("JEV_MEMORY_PILOT_API_KEY", "secret-canary")
    with patch("tools.jev_memory_pilot_api.call_jev", side_effect=failure) as post:
        assert auto(["--corpus", str(corpus), "--json", "--live",
                     "--approved-paid-use", "--max-requests", "1"], repo) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert post.call_count == 1
    assert payload["answer"] == offline
    assert payload["mode"] == "memory_offline"
    assert payload["live_enrichment"] == "skipped"
    assert captured.err == "live_enrichment=skipped\n"
    assert "secret-canary" not in captured.out + captured.err


def test_live_missing_key_and_missing_cost_fall_back(repo_with_graph, tmp_path, monkeypatch, capsys):
    from unittest.mock import patch

    repo, _ = repo_with_graph
    corpus = _private_corpus(tmp_path)
    monkeypatch.delenv("JEV_MEMORY_PILOT_API_KEY", raising=False)
    with patch("tools.jev_memory_pilot_api.call_jev") as post:
        assert auto(["--corpus", str(corpus), "--json", "--live",
                     "--approved-paid-use", "--max-requests", "1"], repo) == 0
    post.assert_not_called()
    assert capsys.readouterr().err == "live_enrichment=skipped\n"

    monkeypatch.setenv("JEV_MEMORY_PILOT_API_KEY", "test-key")
    response = {"model": "typesafe/jev-1.14", "usage": {}, "answers": {
        "p000": {"type": "choice", "choice": "relevant", "probabilities": {
            "relevant": 1.0, "unrelated": 0.0, "insufficient_evidence": 0.0,
        }},
    }}
    with patch("tools.jev_memory_pilot_api.call_jev", return_value=response) as post:
        assert auto(["--corpus", str(corpus), "--json", "--live",
                     "--approved-paid-use", "--max-requests", "1"], repo) == 0
    assert post.call_count == 1
    assert capsys.readouterr().err == "live_enrichment=skipped\n"


def test_valid_live_response_reports_applied_and_cost(
    repo_with_graph, tmp_path, monkeypatch, capsys,
):
    from unittest.mock import patch

    repo, _ = repo_with_graph
    corpus = _private_corpus(tmp_path)
    monkeypatch.setenv("JEV_MEMORY_PILOT_API_KEY", "test-key")
    response = {"model": "typesafe/jev-1.14", "usage": {"cost": 0.000001}, "answers": {
        "p000": {"type": "choice", "choice": "relevant", "probabilities": {
            "relevant": 1.0, "unrelated": 0.0, "insufficient_evidence": 0.0,
        }},
    }}
    with patch("tools.jev_memory_pilot_api.call_jev", return_value=response) as post:
        assert auto(["--corpus", str(corpus), "--json", "--live",
                     "--approved-paid-use", "--max-requests", "1"], repo) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert post.call_count == 1
    assert payload["mode"] == "memory_live"
    assert payload["live_enrichment"] == "applied"
    assert captured.err == "live_enrichment=applied\nJev actual cost: USD 0.00000100\n"
