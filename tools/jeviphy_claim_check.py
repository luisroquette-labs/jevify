"""Reject Jeviphy sales claims that exceed the mechanical scorecard."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from tools.jeviphy_product_score import INTERNAL_PRODUCT_WIN, REPRODUCED_PRODUCT_WIN


COMPARATIVE = re.compile(
    r"\b(faster|better|more effective|more efficient|surpassed|outperformed?)\b",
    re.IGNORECASE,
)
POSITIVE_JEV = re.compile(r"\bjev\b.{0,100}\b(improved|faster|better|more effective|surpassed)\b",
                          re.IGNORECASE | re.DOTALL)


def validate_public_claims(page: str, scorecard: dict) -> None:
    claim = scorecard.get("allowed_claim")
    if not isinstance(claim, str) or not claim:
        raise ValueError("scorecard has no allowed claim")
    if scorecard.get("release") == "technical_beta" and COMPARATIVE.search(page):
        raise ValueError("technical beta page cannot contain comparative claims")
    sections = re.findall(r"<section\b[^>]*>.*?</section>", page, flags=re.IGNORECASE | re.DOTALL)
    outside = re.sub(r"<section\b[^>]*>.*?</section>", "", page,
                     flags=re.IGNORECASE | re.DOTALL)
    for section in [outside, *sections]:
        if COMPARATIVE.search(section):
            if claim not in section or "frozen v2 benchmark" not in section.casefold():
                raise ValueError("comparative claim lacks the allowed claim and benchmark scope")
    if "surpassed" in page.casefold() and claim != REPRODUCED_PRODUCT_WIN:
        raise ValueError("surpassed requires every reproduced product gate")
    if claim == INTERNAL_PRODUCT_WIN and "surpassed" in page.casefold():
        raise ValueError("internal product result cannot become a public superiority claim")
    if POSITIVE_JEV.search(page) and "jev-comparison-artifact" not in page:
        raise ValueError("positive JEV claim requires a separate comparison artifact")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page", type=Path, required=True)
    parser.add_argument("--scorecard", type=Path, required=True)
    args = parser.parse_args()
    validate_public_claims(
        args.page.read_text(encoding="utf-8"),
        json.loads(args.scorecard.read_text(encoding="utf-8")),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
