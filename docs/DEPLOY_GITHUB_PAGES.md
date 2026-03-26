# Deploy no GitHub Pages

## Estrategia adotada

O repositorio publica somente o diretorio `public/` como artefato do GitHub Pages.

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

- scripts, docs e experimentos permanecem no repositorio
- somente o site final fica publico
