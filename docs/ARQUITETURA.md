# Arquitetura

## Objetivo

Fornecer um frontend estatico, leve e publicavel no GitHub Pages para visualizar redes de ensino no Espirito Santo.

## Separacao interna

### `public/`

Diretorio publicado.

- `public/index.html`
- `public/assets/css/styles.css`
- `public/assets/js/app.js`
- `public/data/config/app-config.json`
- `public/data/schools/*.geojson`
- `public/data/density/*.geojson`
- `public/data/boundaries/*.geojson`

### `scripts/`

Ferramentas para transformar os exports do backend no contrato do site.

### `docs/`

Documentacao operacional do frontend.

### `experiments/`

Material local de apoio que nao deve ir ao ar.

## Relacao com o backend

O frontend nao pesquisa fontes oficiais por conta propria.

Ele consome handoffs prontos do backend local, hoje em:

- `D:\Escolas ES\backend\projects\escolas_estaduais_es\data\frontend_exports\`
- `D:\Escolas ES\backend\projects\escolas_municipais_es\data\frontend_exports\`
- `D:\Escolas ES\backend\projects\escolas_federais_es\data\frontend_exports\`

## Publicacao

O GitHub Pages publica apenas `public/`. Isso evita expor scripts, docs e experimentos no site final.
