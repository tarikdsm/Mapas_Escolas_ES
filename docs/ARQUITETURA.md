# Arquitetura

## Objetivo

Fornecer um site estático, leve e publicável no GitHub Pages para visualizar escolas do Espírito Santo por rede de ensino e cruzar essa visão com densidade populacional municipal.

## Camadas do sistema

### Frontend

- `index.html`
- `assets/css/styles.css`
- `assets/js/app.js`
- `assets/js/map-layers.js`
- `assets/js/ui.js`
- `assets/js/utils.js`

### Dados versionados

- `data/config/app-config.json`
- `data/schools/*.geojson`
- `data/density/*.geojson`

### Scripts de geração

- `scripts/build_school_layer.py`
- `scripts/build_density_layer.py`

## Decisões técnicas

- aplicação 100% estática para simplificar o deploy em GitHub Pages
- Leaflet para navegação madura, leve e responsiva
- MarkerCluster para legibilidade em múltiplos níveis de zoom
- configuração de camadas externalizada em JSON
- dados do IBGE incorporados como GeoJSON pronto para reduzir tempo de carregamento no cliente

## Estratégia de expansão

As redes municipais, federais e particulares usam o mesmo contrato de `data/schools/*.geojson`. Quando novos bancos chegarem, basta:

1. normalizar o arquivo com o script correspondente
2. atualizar o `app-config.json` para trocar `status` de `disabled` para `ready`
3. fazer commit e publicar

