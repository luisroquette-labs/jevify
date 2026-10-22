"""Install or uninstall the portable Jeviphy skill with an ownership receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path


RECEIPT = ".jeviphy-install-receipt.json"
DESTINATIONS = {
    "codex": Path(".codex/skills/jeviphy"),
    "claude": Path(".claude/skills/jeviphy"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files(source: Path) -> list[Path]:
    files = []
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"skill source contains symlink: {path.relative_to(source)}")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            files.append(path)
    return files


def read_receipt(destination: Path) -> dict | None:
    path = destination / RECEIPT
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def verify_owned_files(destination: Path, receipt: dict) -> None:
    for relative, expected in receipt["files"].items():
        path = destination / relative
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"installed file changed outside installer: {relative}")


def install(source: Path, destination: Path) -> None:
    existing = read_receipt(destination)
    if destination.exists() and existing is None:
        raise FileExistsError(f"destination already exists without Jeviphy receipt: {destination}")
    if existing:
        verify_owned_files(destination, existing)
        uninstall(destination)
    destination.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for path in source_files(source):
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target, follow_symlinks=False)
        hashes[relative.as_posix()] = digest(target)
    (destination / RECEIPT).write_text(
        json.dumps({"schema_version": 1, "files": hashes}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def uninstall(destination: Path) -> None:
    receipt = read_receipt(destination)
    if receipt is None:
        raise FileNotFoundError(f"Jeviphy receipt not found: {destination}")
    verify_owned_files(destination, receipt)
    for relative in sorted(receipt["files"], reverse=True):
        (destination / relative).unlink()
    (destination / RECEIPT).unlink()
    for cache in destination.rglob("__pycache__"):
        if (
            cache.is_dir()
            and not cache.is_symlink()
            and all(path.is_file() and not path.is_symlink() and path.suffix == ".pyc"
                    for path in cache.iterdir())
        ):
            shutil.rmtree(cache)
    for directory in sorted((path for path in destination.rglob("*") if path.is_dir()), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    if destination.exists() and not any(destination.iterdir()):
        destination.rmdir()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "uninstall"))
    parser.add_argument("--host", choices=("codex", "claude", "both"), default="both")
    parser.add_argument("--home", type=Path, default=Path.home(), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    source = Path(__file__).resolve().parents[1] / "skills" / "jeviphy"
    hosts = ("codex", "claude") if args.host == "both" else (args.host,)
    started = time.perf_counter()
    for host in hosts:
        destination = args.home / DESTINATIONS[host]
        if args.action == "install":
            install(source, destination)
        else:
            uninstall(destination)
    print(json.dumps({"action": args.action, "hosts": hosts, "seconds": time.perf_counter() - started}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
