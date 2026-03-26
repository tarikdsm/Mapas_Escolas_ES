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

O fluxo esperado e:

1. backend gera um GeoJSON ou CSV pronto para handoff
2. frontend normaliza esse arquivo para `public/data/...`
3. frontend sobe somente `public/` no GitHub Pages

## Atualizacao da camada estadual

```powershell
cd D:\Escolas ES\frontend\Mapa_Escolas_ES
python .\scripts\build_school_layer.py `
  --input "..\..\backend\projects\escolas_estaduais_es\data\frontend_exports\escolas_estaduais_es_georef.geojson" `
  --output "public\data\schools\estaduais.geojson" `
  --layer-id "estaduais" `
  --label "E. Estaduais" `
  --color "#2563eb"
```

## Atualizacao da camada municipal

```powershell
cd D:\Escolas ES\frontend\Mapa_Escolas_ES
python .\scripts\build_school_layer.py `
  --input "..\..\backend\projects\escolas_municipais_es\data\frontend_exports\escolas_municipais_es_georef.geojson" `
  --output "public\data\schools\municipais.geojson" `
  --layer-id "municipais" `
  --label "E. Municipais" `
  --color "#2f9d57"
```

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
