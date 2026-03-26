# Mapas das Escolas do Espirito Santo

Repositorio do frontend do mapa, preparado para GitHub Pages.

## Regra de publicacao

Somente `public/` vai para o Pages. Scripts, docs e experimentos ficam no repositorio, mas nao entram no artefato publicado.

## Estrutura

- `public/`: site publicado
- `public/index.html`: shell principal do mapa
- `public/assets/`: CSS e JavaScript
- `public/data/`: camadas e configuracao consumidas pelo site
- `scripts/`: geradores de camada e utilitarios do frontend
- `docs/`: arquitetura, deploy e atualizacao
- `experiments/`: prototipos e HTMLs locais

## Relacao com o backend

Este frontend consome artefatos gerados no backend local em:

- `D:\Escolas ES\backend\projects\escolas_estaduais_es\data\frontend_exports\`
- `D:\Escolas ES\backend\projects\escolas_municipais_es\data\frontend_exports\`
- `D:\Escolas ES\backend\projects\escolas_federais_es\data\frontend_exports\`

O fluxo esperado e:

1. backend gera um GeoJSON ou CSV pronto para handoff
2. frontend gera uma camada otimizada em tiles, com shards de detalhes por municipio
3. frontend sobe somente `public/` no GitHub Pages

## Atualizacao da camada estadual

```powershell
cd D:\Escolas ES\frontend\Mapa_Escolas_ES
python .\scripts\build_school_tiles.py `
  --input "..\..\backend\projects\escolas_estaduais_es\data\frontend_exports\escolas_estaduais_es_georef.geojson" `
  --output-dir "public\data\schools\estaduais" `
  --layer-id "estaduais" `
  --label "E. Estaduais" `
  --color "#2563eb"
```

## Atualizacao da camada municipal

```powershell
cd D:\Escolas ES\frontend\Mapa_Escolas_ES
python .\scripts\build_school_tiles.py `
  --input "..\..\backend\projects\escolas_municipais_es\data\frontend_exports\escolas_municipais_es_georef.geojson" `
  --output-dir "public\data\schools\municipais" `
  --layer-id "municipais" `
  --label "E. Municipais" `
  --color "#2f9d57"
```

## Atualizacao da camada federal

```powershell
cd D:\Escolas ES\frontend\Mapa_Escolas_ES
python .\scripts\build_school_tiles.py `
  --input "..\..\backend\projects\escolas_federais_es\data\frontend_exports\escolas_federais_es_georef.geojson" `
  --output-dir "public\data\schools\federais" `
  --layer-id "federais" `
  --label "E. Federais" `
  --color "#d9485f"
```

## Arquitetura de desempenho

- `public/data/schools/<camada>/index.json`: manifesto leve da camada
- `public/data/schools/<camada>/tiles/...`: tiles estaticos com clusters precomputados e pontos slim
- `public/data/schools/<camada>/details/<municipio>.json`: detalhes por municipio, carregados so no clique
- o mapa carrega apenas tiles do viewport atual e descarta tiles fora da tela

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
