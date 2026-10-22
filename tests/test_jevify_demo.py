"""Keep the public, offline demo runnable on supported Python versions."""

from tools.jevify_demo import main


def test_demo(capsys):
    main()
    output = capsys.readouterr().out
    assert "Synthetic offline decision: auth_validate_token at rank 1" in output
    assert "Evidence: auth_validate_token at auth.py:L3 ↔ synthetic-001" in output
    assert "Graph unchanged; Jev API calls: 0" in output
