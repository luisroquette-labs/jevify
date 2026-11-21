# Ampliar gradualmente o Ruff

## Problema

`pyproject.toml` seleciona apenas `E9`, `F63`, `F7` e `F82`. Um comentário justificava esse conjunto restrito como temporário, sem registrar um plano de correção.

## Critério de conclusão

Medir as violações das demais regras relevantes, registrar o limite inicial por regra e ampliar a seleção sem silenciar erros nem bloquear alterações não relacionadas.

O repositório está com GitHub Issues desativado; este registro acompanha o código até haver um rastreador externo disponível.
