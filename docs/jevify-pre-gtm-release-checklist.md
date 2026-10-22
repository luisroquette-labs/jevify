# Jevify technical beta checklist

## Release decision

Launch as a transparent technical beta. Do not publish a product-advantage claim
over Graphify. Do not restart the paid product benchmark.

## Three-minute demonstration

```bash
git clone https://github.com/luisroquette-labs/jevify.git
python jevify/scripts/install_jevify_skill.py install --host both
cd /path/to/repository
/jevify
```

The bare command discovers the Git repository, chooses a likely question, repairs the graph once when necessary, and answers with the local Graphify path. Source-backed reviewed memory is used only when current and available. The default demonstration requires no provider key, paid API, corpus, or question from the user. Its JSON audit envelope reports the selected repository, graph, question, mode, and whether live enrichment ran.

## Mechanical release decision

1. **Safety or compatibility fails:** stop the release and return to the failing component.
2. **Installation 20/20, zero configuration 30/30, compatibility, and local suite pass:** technical beta.
3. **Any comparison with Graphify:** blocked from current public materials.

## Evidence for the beta

- Twenty clean-install attempts: ten Ubuntu and ten macOS at candidate `a2f7aee0`.
- Thirty zero-configuration cases at the same candidate, with no interaction.
- A passing compatibility receipt and 8,608 local tests.
- CI, CodeQL, dependency audit, and the public-claim checker green on the merged SHA.

## Current boundary

The v13 product benchmark stopped at 0/60. The eight v11 pairs are diagnostic
only. Historical retrieval reports remain available for technical inspection,
but they are not beta claims. JEV is optional, requires separate user approval
for paid use, and has no positive performance claim.
