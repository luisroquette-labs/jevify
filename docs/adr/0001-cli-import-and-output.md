# ADR 0001: Carregamento leve e diretório de saída único

## Contexto

O comando `graphify install` precisa funcionar antes que dependências pesadas de extração estejam disponíveis. O programa também aceita um diretório de saída diferente para cópias de trabalho e execuções com saída compartilhada. Código antigo importa nomes de instalação de `graphify.__main__`.

## Decisão

- Expor a API principal de `graphify` por importação tardia em `graphify.__getattr__`.
- Definir o diretório de saída em `graphify.paths`, aceitando `GRAPHIFY_OUT` relativo ou absoluto, e reutilizá-lo nos controles de caminhos.
- Continuar exportando as funções de instalação por `graphify.__main__` após sua implementação mudar para `graphify.install`.

## Consequências

Instalar não carrega antecipadamente o motor de extração. O mesmo destino é usado pela execução e pelos controles de caminhos. Importações antigas do módulo principal continuam disponíveis.
