# Atualizacao de Dados

## Visao geral

O frontend recebe dados prontos do backend local e os converte para o contrato do site dentro de `public/data/`.

Backend atual de referencia:

- `D:\Escolas ES\backend\projects\escolas_estaduais_es`
- `D:\Escolas ES\backend\projects\escolas_municipais_es`

## Fluxo para escolas

### 1. Obter o export do backend

Use o GeoJSON entregue em:

- `..\..\backend\projects\escolas_estaduais_es\data\frontend_exports\escolas_estaduais_es_georef.geojson`

### 2. Normalizar para o contrato do site

```powershell
python .\scripts\build_school_layer.py `
  --input "..\..\backend\projects\escolas_estaduais_es\data\frontend_exports\escolas_estaduais_es_georef.geojson" `
  --output "public\data\schools\estaduais.geojson" `
  --layer-id "estaduais" `
  --label "E. Estaduais" `
  --color "#2563eb"
```

### Fluxo para escolas municipais

### 1. Obter o export do backend

Use o GeoJSON entregue em:

- `..\..\backend\projects\escolas_municipais_es\data\frontend_exports\escolas_municipais_es_georef.geojson`

### 2. Normalizar para o contrato do site

```powershell
python .\scripts\build_school_layer.py `
  --input "..\..\backend\projects\escolas_municipais_es\data\frontend_exports\escolas_municipais_es_georef.geojson" `
  --output "public\data\schools\municipais.geojson" `
  --layer-id "municipais" `
  --label "E. Municipais" `
  --color "#2f9d57"
```

### 3. Ativar quando a camada estiver pronta

Edite:

- `public/data/config/app-config.json`

### 3. Ativar ou revisar a camada

Edite:

- `public/data/config/app-config.json`

Campos mais comuns:

- `status`
- `defaultVisible`
- `dataPath`

## Fluxo para densidade populacional

```powershell
python .\scripts\build_density_layer.py `
  --output "public\data\density\es_municipios_density.geojson"
```

## Fluxo para o contorno do estado

```powershell
python .\scripts\build_state_boundary.py `
  --input "..\..\backend\projects\escolas_estaduais_es\data\raw\geodata\ibge_municipios_es.geojson" `
  --output "public\data\boundaries\es_state.geojson"
```

## Checklist antes do push

1. Validar o arquivo em `public/data/...`.
2. Conferir `public/data/config/app-config.json`.
3. Abrir `public/index.html` localmente e testar as camadas.
4. Fazer commit apenas no repositorio do frontend.
