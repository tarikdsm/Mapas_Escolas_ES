# Testes

## Objetivo

Dar cobertura automatizada ao que mais importa no projeto:

- funcionalidade do backend e da API
- integridade dos dados exportados para o mapa
- seguranca basica de rotas e tratamento de erro
- disponibilidade das interfaces principais
- regressao de comportamento quando novas features entrarem

As decisoes de teste seguem estas diretrizes:

- escrever codigo testavel, com funcoes pequenas, baixo acoplamento e injecao de dependencias quando isso simplificar mocks e fixtures
- priorizar a piramide de testes: unitarios primeiro, integracao para contratos entre modulos e E2E so nos fluxos mais criticos
- nao considerar uma funcionalidade pronta sem teste automatizado proporcional ao risco
- trabalhar no ciclo Red-Green-Refactor
- sempre reproduzir bugs em teste antes da correcao
- cobrir caminho feliz, bordas e falhas esperadas

## Estrutura

Diretorio dedicado:

- `tests/scripts/`
- `tests/docs/`
- `tests/logs/`

## Como executar

```bash
python tests/scripts/run_tests.py
```

Saida da ultima execucao:

- `tests/logs/latest-test-run.log`

## Automacao

O repositorio roda a suite automaticamente no GitHub Actions em:

- todo `pull_request`
- todo push em `main`
- deploy do GitHub Pages, antes de publicar `public/`

Se algum teste falhar, o deploy publico deve parar e a mudanca nao deve seguir.

## Suite atual

### Unitarios

- helpers puros do backend: limpeza de texto e numeros, composicao de endereco, normalizacao de payload, limites de pagina e importacao a partir de `public/`
- configuracao runtime com injecao de dependencias para facilitar isolamento em teste
- scripts de dados:
  - padronizacao dos datasets escolares
  - classificacao e legenda da densidade demografica
  - reconstrucao do contorno estadual a partir dos municipios

### Backend e API

- healthcheck
- configuracao runtime do frontend
- `/api/meta` declara SQLite como fonte de verdade e snapshots estaticos habilitados
- recriacao do SQLite a partir dos `e_*.json` quando o banco local nao existe
- filtros por municipio com e sem acento
- CRUD completo de escola
- flush administrativo em `POST /api/exports/flush` para forcar a escrita dos snapshots
- inclusao, alteracao e remocao validando ao mesmo tempo SQLite temporario e arquivos `public/data/schools/e_*.json`
- debounce da regravacao estatica em lote, garantindo uma unica exportacao final para mutacoes sequenciais
- `PUT /api/schools/:id` retorna `404` quando a escola nao existe
- `POST` com `Origin` externa recebe `403`
- bind remoto com `ESCOLAS_HOST` nao local exige `ESCOLAS_ALLOW_REMOTE=1`
- `/api/meta` responde `ETag` e devolve `304` quando `If-None-Match` continua atual
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

Escolha a menor camada que cobre o risco:

- unitario para regras puras, formatacao, validacao e transformacoes de dados
- integracao para persistencia SQLite, reexportacao dos snapshots e contratos HTTP
- E2E apenas quando um fluxo do usuario nao puder ser validado de forma mais barata

## Fluxo recomendado

1. criar ou atualizar um teste que reproduza a regra, bug ou regressao
2. executar o teste e confirmar a falha inicial quando houver mudanca de comportamento
3. implementar o minimo para deixar a suite verde
4. refatorar mantendo os testes passando
5. rodar `python tests/scripts/run_tests.py`
6. corrigir qualquer regressao antes de publicar
7. conferir o log salvo em `tests/logs/latest-test-run.log`

## O que sempre validar

- caminho feliz: resposta esperada, persistencia correta e contrato preservado
- casos de borda: valores vazios, nulos, negativos, limites de pagina, datasets vazios e ids inexistentes
- falhas esperadas: validacoes, mensagens de erro, protecoes de rota e bloqueios de entrada invalida

## Isolamento dos testes

- os testes de backend trocam `PUBLIC_ROOT`, `STATIC_CONFIG_PATH` e `DATABASE_PATH` por caminhos temporarios
- cada caso sobe um SQLite proprio em diretório temporario e regrava apenas exports temporarios
- ao final, a infraestrutura confere que o `backend/data/schools.sqlite3` real permaneceu inalterado
