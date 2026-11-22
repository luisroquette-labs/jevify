# ADR 0002: Compatibilidade de importação do manifesto

## Contexto

As funções de manifesto passaram a ser implementadas em `graphify.detect`. O módulo público `graphify.manifest` já expunha esses nomes e pode ser usado por integrações externas.

## Decisão

Manter `graphify.manifest` como ponto de importação que reexporta `save_manifest`, `load_manifest` e `detect_incremental`.

## Consequências

Chamadores antigos podem continuar importando os três nomes. Mudanças futuras nesses nomes precisam considerar os dois caminhos de importação.
