# Jevify X agenda for `@luisroquette`

**Status:** editorial draft. The four new posts below are not queued or published.

## Cadence and release gate

- Keep at least 96 hours between posts from this agenda.
- Publish from `@luisroquette` only.
- Do not begin the new sequence before the 2 November evidence scorecard.
- If the scorecard decision is `pause-outreach`, keep every new row as a draft.
- If the decision is `continue-one-experiment`, queue one row at a time after verifying the previous public URL.

The existing evidence post remains queued for 28 October at 13:30 BRT. It is part of the original launch plan and is not duplicated below.

## Proposed schedule

| Earliest time (BRT) | Purpose | State |
| --- | --- | --- |
| 3 Nov, 13:30 | Explain Jevify in plain language | Draft; conditional on scorecard |
| 7 Nov, 13:30 | Invite people to run the offline demo | Draft; conditional on previous post |
| 11 Nov, 13:30 | Disclose the failed paid Jev result | Draft; conditional on previous post |
| 16 Nov, 13:30 | Ask for an independent reproduction | Draft; conditional on previous post |

## 1. Plain-language explanation

> O Jevify testa uma ideia simples: usar caminhos de arquivos citados por uma memória revisada para orientar a busca do Graphify. No conjunto sintético Click, isso melhorou alguns pontos medidos. Código, método e limites: https://github.com/luisroquette-labs/jevify

## 2. Offline demo

> Quer testar o Jevify sem chave e sem enviar código para fora? Rode `uv run --frozen python -m tools.jevify_demo`. O demo compara a busca base, mostra uma citação de origem e confirma que o grafo não mudou. Instruções: https://github.com/luisroquette-labs/jevify

## 3. What failed

> Nem todo teste deu certo. Em 19 chamadas pagas, o Jev não melhorou os acertos no top 5: 4/19 nos dois braços. Também adicionou latência. Por isso ele continua opcional e fora da afirmação de desempenho do Jevify. Relatório: https://github.com/luisroquette-labs/jevify

## 4. Independent reproduction

> Se você usa Graphify, Claude Mem, Claude Code ou Codex, buscamos uma reprodução independente: commit fixo, mesma pergunta nos dois braços e resultado positivo ou negativo. Queremos testar os limites da ideia com transparência. https://github.com/luisroquette-labs/jevify

## Publication checks

Antes de colocar cada post na fila:

1. Confirm the preceding row has a terminal public URL or was intentionally skipped.
2. Recheck that the repository and evidence page still support every number and statement.
3. Preserve the exact reviewed copy; a material edit requires another review.
4. Store the resulting X post ID, URL, and timestamp in the launch scorecard.
5. Stop the sequence after a substantive maintainer response and evaluate that response first.
