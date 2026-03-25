# Deploy no GitHub Pages

## Estratégia adotada

O repositório publica a própria raiz como artefato do GitHub Pages usando GitHub Actions.

Arquivo-chave:

- `.github/workflows/deploy-pages.yml`

## Como funciona

1. Push em `main`.
2. O workflow instala o ambiente do Pages.
3. O conteúdo do repositório é enviado como artefato.
4. O GitHub Pages publica a aplicação.

## Observação importante do primeiro deploy

Se o repositório ainda não tiver Pages habilitado, o passo `configure-pages` falha com erro equivalente a `Get Pages site failed`.

Há duas formas suportadas:

1. Habilitar manualmente em `Settings > Pages > Build and deployment > GitHub Actions`.
2. Criar o secret `PAGES_PAT` e deixar o workflow tentar a habilitação automática.

O secret é opcional. Sem ele, a habilitação manual inicial continua sendo o caminho mais simples.

## Configuração esperada no repositório

Na interface do GitHub:

1. Abrir `Settings`.
2. Ir em `Pages`.
3. Selecionar `GitHub Actions` como fonte de deploy, se o repositório ainda não estiver configurado.
