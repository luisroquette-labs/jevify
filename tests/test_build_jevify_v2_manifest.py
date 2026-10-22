from tools.build_jevify_v2_manifest import changed_files, language_for, stable_key


def test_changed_files_are_unique_and_ordered():
    patch = """diff --git a/src/a.ts b/src/a.ts
diff --git a/src/b.ts b/src/b.ts
diff --git a/src/a.ts b/src/a.ts
"""
    assert changed_files(patch) == ("src/a.ts", "src/b.ts")


def test_language_uses_solution_patch_and_cpp_header_repos():
    assert language_for({"repo": "example/repo", "patch": "diff --git a/x.go b/x.go\n"}) == "Go"
    assert language_for({"repo": "fmtlib/fmt", "patch": "diff --git a/x.h b/x.h\n"}) == "C++"


def test_stable_key_is_repeatable_and_salted():
    assert stable_key("case", "select") == stable_key("case", "select")
    assert stable_key("case", "select") != stable_key("case", "holdout")
