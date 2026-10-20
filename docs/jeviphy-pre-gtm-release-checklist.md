# Jeviphy pre-GTM release checklist

## Three-minute demonstration

```bash
git clone https://github.com/luisroquette-labs/jeviphy.git
python jeviphy/scripts/install_jeviphy_skill.py install --host both
cd /path/to/repository
/jeviphy
```

The bare command discovers the Git repository, chooses a likely question, repairs the graph once when necessary, and answers with the local Graphify path. Source-backed reviewed memory is used only when current and available. The default demonstration requires no provider key, paid API, corpus, or question from the user. Its JSON audit envelope reports the selected repository, graph, question, mode, and whether live enrichment ran.

## Mechanical release decision

1. **Safety or compatibility fails:** stop the release and return to the failing component.
2. **Retrieval, usability, and compatibility pass:** limited source-aware beta only.
3. **Product passes and reproduction is pending:** internal candidate only.
4. **Every gate passes:** private beta may quote the exact scorecard claim.

## Evidence required for the final candidate

- A sealed 120-pair product report produced by the official SWE-bench evaluator.
- Twenty clean-install attempts: ten Ubuntu and ten macOS at the exact candidate SHA.
- A fresh 30-case zero-configuration report when any runner, installer, or Graphify query path changed.
- Two independent retrieval receipts, including one Linux reviewer.
- CI, CodeQL, dependency audit, Graphify integrity, and the public-claim checker green on the merged SHA.

## Current boundary

The frozen v2 retrieval result supports only its source-backed retrieval claim. Product success, final two-OS usability, and independent reproduction remain open. JEV is optional and has no positive claim.
