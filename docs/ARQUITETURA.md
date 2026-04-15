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
- `backend/data/*.sqlite3`: banco local

### `scripts/`

Ferramentas para transformar os exports do backend no contrato do site.

### `docs/`

Documentacao operacional do frontend.

### `experiments/`

Material local de apoio que nao deve ir ao ar.

## Fluxo local

1. `python3 backend/server.py` sobe um servidor unico em `http://127.0.0.1:8765`
2. o mapa abre em `/`
3. o painel administrativo abre em `/admin/`
4. a API responde em `/api/`
5. o backend importa a base atual para o SQLite na primeira execucao
6. edicoes no painel atualizam o banco e regravam os arquivos `public/data/schools/e_*.json`

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
