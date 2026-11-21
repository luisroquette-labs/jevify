from scripts.check_comments import check, comment_lines, increases, toml_comment_lines


def test_comment_scanner_ignores_strings_and_required_headers():
    source = '#!/usr/bin/env python3\n# coding: utf-8\nurl = "https://example.com/#part"\n# remove\n'
    assert comment_lines(source) == [4]
    assert comment_lines("x = 1  #! not a shebang\n") == [1]
    assert comment_lines("x = 1  # coding: utf-8\n") == [1]


def test_required_comment_needs_exact_text():
    assert comment_lines("# Copyright 2026 COESA\n", {"# Copyright 2026 COESA"}) == []
    assert comment_lines("# Copyright 2026 someone else\n", {"# Copyright 2026 COESA"}) == [1]


def test_toml_scanner_ignores_hashes_inside_strings():
    source = "key = '#literal' # remove\nother = \"escaped \\\"#literal\\\"\"\ntext = '''\n#literal\n'''\n# remove\n"
    assert toml_comment_lines(source) == [1, 6]
    assert toml_comment_lines('key = """abc"""" # remove\n') == [1]
    assert toml_comment_lines("key = '''abc'''' # remove\n") == [1]


def test_counts_only_cached_files_and_respects_python_encoding(tmp_path, monkeypatch):
    from scripts import check_comments

    (tmp_path / "latin.py").write_bytes(b"# coding: latin-1\nname = '\xe9'\n# remove\n")
    (tmp_path / "scratch.py").write_text("# not tracked\n")
    (tmp_path / "pyproject.toml").write_text('key = "#value" # remove\n')
    monkeypatch.setattr(check_comments, "ROOT", tmp_path)
    monkeypatch.setattr(
        check_comments.subprocess,
        "check_output",
        lambda *args, **kwargs: b"latin.py\0pyproject.toml\0",
    )
    assert check_comments.counts() == {"latin.py": 1, "pyproject.toml": 1}


def test_ratchet_rejects_new_comments_and_stale_baseline():
    assert check({"a.py": 1}, {"a.py": 0}) == ["a.py: 1 comment lines; allowed 0"]
    assert check({"a.py": 0}, {"a.py": 1}) == [
        "a.py: baseline is stale (0 comment lines; allowed 1)"
    ]
    assert increases({"a.py": 2, "b.py": 0}, {"a.py": 1, "b.py": 1}) == [
        "a.py: 2 comment lines; allowed 1"
    ]


def test_comment_baseline_is_current():
    from scripts.check_comments import BASELINE, counts
    import json

    assert check(counts(), json.loads(BASELINE.read_text())) == []
