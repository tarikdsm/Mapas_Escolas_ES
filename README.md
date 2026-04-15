# Mapas das Escolas do Espirito Santo

Repositorio com frontend do mapa, backend local em Python e banco SQLite unificado.

## Como rodar localmente

```bash
python3 backend/server.py
```

URLs locais:

- mapa: `http://127.0.0.1:8765/`
- backend administrativo: `http://127.0.0.1:8765/admin/`
- API: `http://127.0.0.1:8765/api/`

## Regra de publicacao

Somente `public/` vai para o GitHub Pages. Scripts, docs, banco SQLite e backend Python ficam no repositorio e nao entram no artefato publicado.

## Estrutura

- `public/`: site publicado
- `public/index.html`: shell principal do mapa
- `public/assets/`: CSS e JavaScript
- `public/data/`: camadas e configuracao consumidas pelo site
- `scripts/`: geradores de camada e utilitarios do frontend
- `docs/`: arquitetura, deploy e atualizacao
- `experiments/`: prototipos e HTMLs locais

## Relacao entre frontend e backend

O backend local:

1. importa os snapshots atuais `public/data/schools/e_*.json` para um banco SQLite unico
2. expoe CRUD e consulta por API
3. serve o mapa em `/` e o painel em `/admin/`
4. regrava os arquivos `public/data/schools/e_*.json` sempre que uma escola e criada, alterada ou excluida

O frontend local tenta carregar `/api/config` primeiro. Quando a API existe, ele consome os datasets pela API. No GitHub Pages, sem backend, ele volta automaticamente para os arquivos estaticos publicados em `public/data/`.

## GitHub Pages

No GitHub Pages ficam publicados:

- o mapa em modo estatico
- o painel administrativo em modo somente leitura

O Pages nao hospeda SQLite nem API com escrita. O modo completo de edicao roda localmente com `python3 backend/server.py`.

## Dados escolares publicados

Os datasets estaticos publicados e mantidos pelo backend sao:

- `public/data/schools/e_municipais.json`
- `public/data/schools/e_estaduais.json`
- `public/data/schools/e_federais.json`
- `public/data/schools/e_privadas.json`

Eles continuam separados por rede para o frontend saber o tipo da escola, e tambem servem como snapshot para o GitHub Pages e bootstrap da primeira carga do banco local.

## Documentacao principal

- `docs/ARQUITETURA.md`
- `docs/API_BACKEND.md`
- `docs/TESTES.md`
- `docs/DEPLOY_GITHUB_PAGES.md`
- `docs/ATUALIZACAO_DE_DADOS.md`

## Testes

Runner principal:

```bash
python3 tests/scripts/run_tests.py
```

Estrutura:

- `tests/scripts/`
- `tests/docs/`
- `tests/logs/`

## Atualizacao da densidade populacional

```powershell
python .\scripts\build_density_layer.py `
  --output "public\data\density\es_municipios_density.geojson"
```

## Atualizacao do contorno do estado

```powershell
python .\scripts\build_state_boundary.py `
  --input "..\..\backend\projects\escolas_estaduais_es\data\raw\geodata\ibge_municipios_es.geojson" `
  --output "public\data\boundaries\es_state.geojson"
```
