import io
import json
import os
import re
import subprocess
import sys
import tokenize
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = Path(__file__).with_name("comment-baseline.json")
REQUIRED = Path(__file__).with_name("required-comments.json")


def comment_lines(source: str, required: set[str] | None = None) -> list[int]:
    required = required or set()
    lines = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        line, _ = token.start
        body = token.string
        on_own_line = not token.line[: token.start[1]].strip()
        if line == 1 and on_own_line and body.startswith("#!"):
            continue
        if line <= 2 and on_own_line and re.search(r"coding[:=]\s*[-\w.]+", body):
            continue
        if body in required:
            continue
        lines.append(line)
    return lines


def toml_comment_lines(source: str) -> list[int]:
    lines = []
    multiline = ""
    for number, line in enumerate(source.splitlines(), 1):
        quote = multiline
        index = 0
        while index < len(line):
            char = line[index]
            if quote:
                if char == "\\" and quote.startswith('"'):
                    index += 2
                    continue
                if line.startswith(quote, index):
                    if len(quote) == 3:
                        closing = 3
                        while closing < 5 and line[index + closing : index + closing + 1] == quote[0]:
                            closing += 1
                        index += closing
                    else:
                        index += len(quote)
                    quote = ""
                    multiline = ""
                    continue
                index += 1
                continue
            if char == "#":
                lines.append(number)
                break
            if char in ('"', "'"):
                triple = char * 3
                quote = triple if line.startswith(triple, index) else char
                if len(quote) == 3:
                    multiline = quote
                index += len(quote)
                continue
            index += 1
    return lines


def counts() -> dict[str, int]:
    required = json.loads(REQUIRED.read_text())
    tracked = subprocess.check_output(
        ["git", "ls-files", "--cached", "-z"], cwd=ROOT
    )
    tracked = os.fsdecode(tracked).split("\0")
    files = sorted(file for file in tracked if file.endswith(".py") and (ROOT / file).is_file())
    current = {}
    for file in files:
        with tokenize.open(ROOT / file) as source:
            current[file] = len(comment_lines(source.read(), set(required.get(file, []))))
    if "pyproject.toml" in tracked:
        current["pyproject.toml"] = len(toml_comment_lines((ROOT / "pyproject.toml").read_text()))
    return current


def increases(current: dict[str, int], baseline: dict[str, int]) -> list[str]:
    return [
        f"{file}: {count} comment lines; allowed {baseline.get(file, 0)}"
        for file, count in current.items()
        if count > baseline.get(file, 0)
    ]


def check(current: dict[str, int], baseline: dict[str, int]) -> list[str]:
    failures = increases(current, baseline)
    failures.extend(
        f"{file}: baseline is stale ({current.get(file, 0)} comment lines; allowed {allowed})"
        for file, allowed in baseline.items()
        if current.get(file, 0) < allowed
    )
    return failures


def main() -> int:
    current = counts()
    baseline = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    if "--write-baseline" in sys.argv:
        failures = increases(current, baseline) if BASELINE.exists() else []
        if not failures:
            BASELINE.write_text(json.dumps(current, indent=2) + "\n")
    else:
        failures = check(current, baseline)
    if failures:
        print("Comment ratchet failed:\n" + "\n".join(failures), file=sys.stderr)
        return 1
    print(f"Comment ratchet passed: {sum(current.values())} remaining comment lines.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
