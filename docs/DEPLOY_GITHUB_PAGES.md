# Deploy no GitHub Pages

## Estrategia adotada

O repositorio publica somente o diretorio `public/` como artefato do GitHub Pages.

Isso significa que o deploy publico inclui:

- o mapa do frontend
- o painel administrativo em modo somente leitura

Isso nao inclui:

- a API em `/api/`
- o banco SQLite local
- o codigo Python do backend

Arquivo-chave:

- `.github/workflows/deploy-pages.yml`

## Como funciona

1. Push em `main`.
2. O workflow faz checkout do repositorio do frontend.
3. O artefato enviado ao Pages e apenas `public/`.
4. O GitHub Pages publica o site.

## Primeiro deploy

Se o Pages ainda nao estiver habilitado:

1. Abra `Settings > Pages`.
2. Em `Build and deployment`, selecione `GitHub Actions`.
3. Rode o workflow novamente.

## Resultado esperado

- scripts, docs, banco e backend permanecem no repositorio
- `public/` sobe com o mapa e o painel estatico
- o Pages nao permite escrita no banco nem CRUD real

## Fluxo recomendado para publicar dados atualizados

1. Rode o backend local com `python3 backend/server.py`.
2. Edite a base pelo painel em `http://127.0.0.1:8765/admin/`.
3. O backend regrava automaticamente `public/data/schools/e_*.json`.
4. Faça commit e push dessas alteracoes.
5. O GitHub Pages publica o novo snapshot estatico.
