import json

import pytest

from tools.jevify_install_eval import (
    InstallRecord,
    run_attempt,
    score_installs,
    write_install_score,
)


def _record(index, os_name, *, success=True, candidate="a" * 40):
    return InstallRecord(
        attempt_id=f"{os_name}-{index}", operating_system=os_name,
        host="claude" if index % 2 else "codex", jevify_commit=candidate,
        success=success, seconds=20 + index, install_stdout_sha256="1" * 64,
        install_stderr_sha256="2" * 64, query_stdout_sha256="3" * 64,
        query_stderr_sha256="4" * 64, diagnostic=None,
    )


def test_install_score_requires_twenty_attempts_and_both_systems():
    records = [_record(i, "Ubuntu") for i in range(10)] + [
        _record(i, "macOS") for i in range(10)
    ]
    score = score_installs(records)
    assert score["attempts"] == 20
    assert score["successes"] == 20
    assert score["operating_systems"] == ["Ubuntu", "macOS"]


def test_install_score_rejects_mixed_candidates_and_duplicate_attempts():
    records = [_record(i, "Ubuntu") for i in range(10)] + [
        _record(i, "macOS") for i in range(10)
    ]
    records[-1] = _record(9, "macOS", candidate="b" * 40)
    with pytest.raises(ValueError, match="candidate"):
        score_installs(records)
    with pytest.raises(ValueError, match="duplicate"):
        score_installs([records[0], records[0]])


def test_clean_attempt_installs_queries_reinstalls_and_uninstalls(tmp_path):
    record = run_attempt(tmp_path, host="codex", operating_system="Ubuntu", index=0,
                         candidate="a" * 40)
    assert record.success is True
    assert not (tmp_path / "home" / ".codex/skills/jevify").exists()
    assert len(record.query_stdout_sha256) == 64


def test_write_install_score_seals_two_canonical_journals(tmp_path):
    journals = []
    records = [*(_record(i, "Ubuntu") for i in range(10)),
               *(_record(i, "macOS") for i in range(10))]
    for offset, os_name in ((0, "Ubuntu"), (10, "macOS")):
        journal = tmp_path / f"{os_name}.jsonl"
        journal.write_text("".join(
            json.dumps(record.__dict__, sort_keys=True) + "\n"
            for record in records[offset:offset + 10]
        ))
        journals.append(journal)
    output = tmp_path / "install-score.json"
    score = write_install_score(journals, output)
    assert score["status"] == "pass"
    assert len(score["journal_sha256"]) == 64
    assert json.loads(output.read_text()) == score


def test_write_install_score_rejects_noncanonical_journal(tmp_path):
    journal = tmp_path / "records.jsonl"
    journal.write_text(json.dumps(_record(0, "Ubuntu").__dict__) + "\n")
    with pytest.raises(ValueError, match="non-canonical"):
        write_install_score([journal], tmp_path / "score.json")


def test_write_install_score_rejects_non_boolean_success(tmp_path):
    journal = tmp_path / "records.jsonl"
    payload = {**_record(0, "Ubuntu").__dict__, "success": "yes"}
    journal.write_text(json.dumps(payload, sort_keys=True) + "\n")
    with pytest.raises(ValueError, match="invalid install record"):
        write_install_score([journal], tmp_path / "score.json")


def test_install_matrix_file_is_frozen():
    matrix = json.loads(open("benchmarks/jevify-v2/install-matrix.json").read())
    assert matrix == {
        "schema_version": 1,
        "attempts": [
            {"os": "Ubuntu", "host": "claude", "repeat": 5},
            {"os": "Ubuntu", "host": "codex", "repeat": 5},
            {"os": "macOS", "host": "claude", "repeat": 5},
            {"os": "macOS", "host": "codex", "repeat": 5},
        ],
    }
