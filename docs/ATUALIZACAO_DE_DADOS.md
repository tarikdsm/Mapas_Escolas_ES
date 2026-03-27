# Atualizacao de Dados

## Visao geral

O frontend agora consome diretamente quatro arquivos padronizados para as escolas:

- `public/data/schools/e_estaduais.json`
- `public/data/schools/e_municipais.json`
- `public/data/schools/e_federais.json`
- `public/data/schools/e_privadas.json`

As bases originais do backend continuam intactas. O frontend usa apenas esses quatro arquivos para plotar os pontos no mapa e preencher o card/popup das escolas.

## Contrato padronizado

Cada registro escolar possui somente estes campos:

- `Nome_escola`
- `Endereco`
- `Municipio`
- `CEP`
- `telefone`
- `email`
- `Latitude`
- `Longitude`
- `Numero_professores`
- `Numero_alunos`

## Fontes do backend

Os quatro arquivos sao gerados a partir destes GeoJSONs do backend:

- `..\..\backend\projects\escolas_estaduais_es\data\frontend_exports\escolas_estaduais_es_georef.geojson`
- `..\..\backend\projects\escolas_municipais_es\data\frontend_exports\escolas_municipais_es_georef.geojson`
- `..\..\backend\projects\escolas_federais_es\data\frontend_exports\escolas_federais_es_georef.geojson`
- `..\..\backend\projects\escolas_particulares_es\data\frontend_exports\escolas_particulares_es_georef.geojson`

## Como regenerar

```powershell
python .\scripts\build_standardized_school_data.py
```

O script recria:

- `public/data/schools/e_estaduais.json`
- `public/data/schools/e_municipais.json`
- `public/data/schools/e_federais.json`
- `public/data/schools/e_privadas.json`

## Densidade populacional

A camada de densidade continua separada:

```powershell
python .\scripts\build_density_layer.py `
  --output "public\data\density\es_municipios_density.geojson"
```

## Contorno do estado

```powershell
python .\scripts\build_state_boundary.py `
  --input "..\..\backend\projects\escolas_estaduais_es\data\raw\geodata\ibge_municipios_es.geojson" `
  --output "public\data\boundaries\es_state.geojson"
```

## Checklist

1. Rodar `python .\scripts\build_standardized_school_data.py`.
2. Conferir se os quatro arquivos `e_*.json` foram atualizados.
3. Validar `public/data/config/app-config.json`.
4. Abrir `public/index.html` e testar as camadas no mapa.
