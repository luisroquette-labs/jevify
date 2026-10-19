import hashlib
from pathlib import Path

from tools.jeviphy_eval_contract import STRATUM_COUNTS, load_manifest


def test_public_manifest_satisfies_frozen_contract():
    manifest = load_manifest(Path("benchmarks/jeviphy-v2/manifest.json"))
    assert len(manifest.cases) == 120
    assert sum(case.holdout for case in manifest.cases) == 20
    assert len(manifest.repos) >= 6
    assert {case.stratum for case in manifest.cases} == set(STRATUM_COUNTS)


def test_public_manifest_hash_is_pinned():
    manifest = Path("benchmarks/jeviphy-v2/manifest.json")
    expected = Path("benchmarks/jeviphy-v2/MANIFEST.sha256").read_text().split()[0]
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == expected
