# Arquitetura

## Objetivo

Separar mapa e administracao sem perder a fluidez do frontend atual.

O projeto agora tem:

- frontend do mapa em `public/`
- backend local em `backend/server.py`
- banco SQLite unico em `backend/data/`
- API HTTP para consulta e CRUD
- painel administrativo em `public/admin/`

## Separacao interna

### `public/`

Diretorio publicado e tambem servido localmente pelo backend.

- `public/index.html`
- `public/admin/index.html`
- `public/assets/css/styles.css`
- `public/assets/css/admin.css`
- `public/assets/js/app.js`
- `public/assets/js/admin.js`
- `public/data/config/app-config.json`
- `public/data/schools/e_*.json`
- `public/data/density/*.geojson`
- `public/data/boundaries/*.geojson`

### `backend/`

Servidor local em Python sem dependencias externas obrigatorias.

- `backend/server.py`: servidor HTTP, API REST, importacao inicial e persistencia SQLite
- `backend/data/*.sqlite3`: banco local e fonte de verdade operacional; os snapshots `e_*.json` sao artefatos gerados e fallback de recuperacao

### `scripts/`

Ferramentas para transformar os exports do backend no contrato do site.

### `docs/`

Documentacao operacional do frontend.

## Fluxo local

1. `python3 backend/server.py` sobe um servidor unico em `http://127.0.0.1:8765`
2. o mapa abre em `/`
3. o painel administrativo abre em `/admin/`
4. a API responde em `/api/`
5. o SQLite e a base principal do modo local
6. se o SQLite nao existir, o backend recria o banco a partir dos snapshots `public/data/schools/e_*.json`
7. toda edicao passa pelo SQLite e so depois atualiza os snapshots publicados
8. `POST /api/exports/flush` permite forcar a regravacao estatica quando necessario
9. bind remoto so e permitido com `ESCOLAS_ALLOW_REMOTE=1`, e as rotas mutantes exigem `Origin` compativel com o `Host`

## Fluxo no GitHub Pages

1. apenas `public/` e publicado
2. o mapa roda com os arquivos estaticos versionados
3. o painel abre, mas entra em modo somente leitura
4. a API local e o SQLite nao sao publicados no Pages

## Snapshots atuais do mapa

- municipais: `public/data/schools/e_municipais.json`
- estaduais: `public/data/schools/e_estaduais.json`
- federais: `public/data/schools/e_federais.json`
- privadas: `public/data/schools/e_privadas.json`

A estrutura antiga com `tiles/`, `details/` e `index.json` por rede foi removida. O backend e o frontend local agora partem do mesmo contrato `e_*.json`.

Os arquivos `e_*.json` continuam sendo o snapshot versionado e a base publicada no GitHub Pages. O SQLite local e a fonte de verdade do modo completo; os JSONs sao reexportados a partir dele.

## Contrato do frontend

O frontend continua consumindo datasets leves por rede.

Local:

- tenta `GET /api/config`
- recebe caminhos de dados via API, como `/api/frontend/schools/estaduais`

GitHub Pages:

- cai automaticamente no fallback `public/data/config/app-config.json`
- le os arquivos `public/data/schools/e_*.json`

## Publicacao

O GitHub Pages publica apenas `public/`. Isso evita expor scripts, docs, banco e codigo do backend local no site final.
