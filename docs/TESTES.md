# Testes

## Objetivo

Dar cobertura automatizada ao que mais importa no projeto:

- funcionalidade do backend e da API
- integridade dos dados exportados para o mapa
- seguranca basica de rotas e tratamento de erro
- disponibilidade das interfaces principais
- regressao de comportamento quando novas features entrarem

## Estrutura

Diretorio dedicado:

- `tests/scripts/`
- `tests/docs/`
- `tests/logs/`

## Como executar

```bash
python3 tests/scripts/run_tests.py
```

Saida da ultima execucao:

- `tests/logs/latest-test-run.log`

## Suite atual

### Backend e API

- healthcheck
- configuracao runtime do frontend
- filtros por municipio com e sem acento
- CRUD completo de escola
- atualizacao automatica dos exports `e_*.json`
- protecao contra path traversal em arquivos estaticos
- nao exposicao de detalhes internos em erro 500
- limite para corpo de requisicao grande
- verificacao simples de tempo de resposta para listagem

### Frontend estatico

- pagina do mapa responde
- pagina administrativa responde
- assets principais sao servidos
- links cruzados entre mapa e backend existem

## Regra para evolucao

Toda mudanca relevante no projeto deve trazer testes novos ou ampliar testes existentes quando afetar:

- contrato de API
- fluxo de CRUD
- formato dos dados consumidos pelo mapa
- comportamento do painel administrativo
- controles de seguranca
- desempenho de endpoints criticos

## Fluxo recomendado

1. implementar ou alterar a funcionalidade
2. adicionar ou ajustar testes em `tests/scripts/`
3. rodar `python3 tests/scripts/run_tests.py`
4. corrigir regressao antes de publicar
5. conferir o log salvo em `tests/logs/latest-test-run.log`
