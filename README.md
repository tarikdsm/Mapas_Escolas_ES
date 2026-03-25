# Mapas das Escolas do Espírito Santo

Site estático para GitHub Pages com foco visual exclusivo no território do Espírito Santo, preparado para receber múltiplas redes de ensino e uma camada oficial de densidade populacional municipal.

## O que este repositório entrega

- mapa interativo em tela cheia com navegação estilo web map
- camada operacional da rede estadual com clusterização responsiva
- estrutura pronta para redes municipais, federais e particulares
- choropleth de densidade populacional por município do ES com fonte oficial do IBGE
- documentação operacional para atualizar dados e publicar no GitHub Pages

## Estrutura

- `index.html`: shell principal do site
- `assets/`: CSS e JavaScript do frontend
- `data/config/app-config.json`: configuração das camadas e do mapa
- `data/schools/`: camadas GeoJSON por rede de ensino
- `data/density/`: camada de densidade populacional oficial
- `scripts/`: utilitários para regenerar as camadas
- `docs/`: arquitetura, atualização de dados, fontes e deploy

## Publicação

O repositório já inclui workflow para GitHub Pages em `.github/workflows/deploy-pages.yml`.

## Primeiro deploy

Na primeira publicação, o repositório precisa estar com GitHub Pages habilitado.

Sem segredo adicional:

1. Abra `Settings > Pages`.
2. Em `Build and deployment`, selecione `GitHub Actions`.
3. Salve e rode o workflow novamente.

Com automação de enablement:

- crie um secret de repositório chamado `PAGES_PAT`
- use um Personal Access Token com permissão para administração/pages do repositório
- o workflow tentará habilitar o Pages automaticamente

## Atualização das escolas estaduais

```bash
python scripts/build_school_layer.py \
  --input "/caminho/para/escolas_estaduais_es_georef.geojson" \
  --output "data/schools/estaduais.geojson" \
  --layer-id "estaduais" \
  --label "E. Estaduais" \
  --color "#2563eb"
```

## Atualização da densidade populacional

```bash
python scripts/build_density_layer.py \
  --output "data/density/es_municipios_density.geojson"
```

## Documentação recomendada

- `docs/ARQUITETURA.md`
- `docs/ATUALIZACAO_DE_DADOS.md`
- `docs/FONTES_OFICIAIS.md`
- `docs/DEPLOY_GITHUB_PAGES.md`
