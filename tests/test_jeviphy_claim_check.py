import json

import pytest

from tools.jeviphy_claim_check import validate_public_claims
from tools.jeviphy_product_score import REPRODUCED_PRODUCT_WIN, RETRIEVAL_ONLY


def test_unscoped_faster_claim_is_rejected():
    with pytest.raises(ValueError, match="benchmark scope"):
        validate_public_claims("<main>Jeviphy is faster.</main>", {"allowed_claim": RETRIEVAL_ONLY})


def test_scoped_retrieval_claim_is_allowed():
    page = (
        "<section><h2>" + RETRIEVAL_ONLY + "</h2>"
        "<p>Faster retrieval in the frozen v2 benchmark.</p></section>"
    )
    validate_public_claims(page, {"allowed_claim": RETRIEVAL_ONLY})


def test_surpassed_requires_reproduced_product_claim():
    page = (
        "<section><h2>" + REPRODUCED_PRODUCT_WIN + "</h2>"
        "<p>Surpassed in the frozen v2 benchmark.</p></section>"
    )
    validate_public_claims(page, {"allowed_claim": REPRODUCED_PRODUCT_WIN})
    with pytest.raises(ValueError):
        validate_public_claims(page.replace(REPRODUCED_PRODUCT_WIN, RETRIEVAL_ONLY),
                               {"allowed_claim": RETRIEVAL_ONLY})


def test_positive_jev_attribution_requires_its_own_artifact():
    page = "<section>Jev improved retrieval.</section>"
    with pytest.raises(ValueError, match="JEV"):
        validate_public_claims(page, {"allowed_claim": RETRIEVAL_ONLY})


@pytest.mark.parametrize(
    "copy",
    ["Faster in the frozen v2 benchmark.", "More efficient than Graphify.", "Outperformed Graphify."],
)
def test_technical_beta_rejects_even_scoped_comparative_claims(copy):
    scorecard = {"release": "technical_beta", "allowed_claim": "Technical beta."}
    with pytest.raises(ValueError, match="technical beta"):
        validate_public_claims(f"<section>{copy}</section>", scorecard)


def test_current_sales_page_matches_committed_scorecard():
    scorecard = json.loads(open("benchmarks/jeviphy-beta/scorecard.json").read())
    page = open("docs/jeviphy/index.html").read()
    validate_public_claims(page, scorecard)
