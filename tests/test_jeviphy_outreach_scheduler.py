import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts/jeviphy_outreach_scheduler.py"
SPEC = importlib.util.spec_from_file_location("jeviphy_outreach_scheduler", SCRIPT)
assert SPEC and SPEC.loader
scheduler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scheduler)


def test_before_due_does_not_call_action(monkeypatch, tmp_path):
    called = []
    monkeypatch.setitem(scheduler.ACTIONS, "graphify_comment", lambda: called.append(True))
    monkeypatch.setattr(
        "sys.argv",
        [
            "scheduler",
            "--now",
            "2026-10-21T10:29:59-03:00",
            "--state-file",
            str(tmp_path / "state.json"),
        ],
    )
    assert scheduler.main() == 0
    assert called == []


def test_graphify_remote_marker_prevents_duplicate(monkeypatch):
    calls = []

    def fake_run_gh(args):
        calls.append(args)
        return "<!-- jeviphy-outreach:graphify-evidence-v1 -->" if "api" in args else ""

    monkeypatch.setattr(scheduler, "run_gh", fake_run_gh)
    assert scheduler.graphify_comment() == "already_present"
    assert len(calls) == 1


def test_claude_mem_remote_marker_prevents_duplicate(monkeypatch):
    payload = {
        "data": {
            "repository": {
                "id": "repo-id",
                "discussionCategories": {"nodes": [{"id": "category-id", "name": "Ideas"}]},
                "discussions": {
                    "nodes": [
                        {
                            "body": "<!-- jeviphy-outreach:claude-mem-source-paths-v1 -->",
                            "url": "https://github.com/thedotmack/claude-mem/discussions/1",
                        }
                    ]
                },
            }
        }
    }
    calls = []

    def fake_run_gh(args):
        calls.append(args)
        return json.dumps(payload)

    monkeypatch.setattr(scheduler, "run_gh", fake_run_gh)
    assert scheduler.claude_mem_discussion() == "already_present"
    assert len(calls) == 1


def test_local_completion_prevents_duplicate(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"graphify-evidence-v1": {"outcome": "published"}}))
    called = []
    monkeypatch.setitem(scheduler.ACTIONS, "graphify_comment", lambda: called.append(True))
    monkeypatch.setattr(
        "sys.argv",
        [
            "scheduler",
            "--now",
            "2026-10-22T10:30:00-03:00",
            "--state-file",
            str(state_file),
        ],
    )
    assert scheduler.main() == 0
    assert called == []


def test_failed_action_does_not_persist_state(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    monkeypatch.setitem(
        scheduler.ACTIONS,
        "graphify_comment",
        lambda: (_ for _ in ()).throw(RuntimeError("provider failed")),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "scheduler",
            "--now",
            "2026-10-21T10:30:00-03:00",
            "--state-file",
            str(state_file),
        ],
    )
    with pytest.raises(RuntimeError, match="provider failed"):
        scheduler.main()
    assert not state_file.exists() or json.loads(state_file.read_text()) == {}
