# Atualizacao de Dados

## Visao geral

Agora existe uma base unica no backend local.

O frontend continua consumindo quatro datasets padronizados por rede:

- `public/data/schools/e_estaduais.json`
- `public/data/schools/e_municipais.json`
- `public/data/schools/e_federais.json`
- `public/data/schools/e_privadas.json`

Localmente, o mapa pode ler os dados pela API. Para GitHub Pages, o backend regrava esses quatro arquivos estaticos sempre que uma escola e salva ou excluida no painel administrativo.

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

## Fonte unica atual

O backend local importa os snapshots `public/data/schools/e_*.json` para um SQLite unico em:

- `backend/data/schools.sqlite3`

As escolas continuam identificando a rede em `network_type`, com os valores:

- `municipais`
- `estaduais`
- `federais`
- `privadas`

## Como atualizar pela interface

1. Rode `python3 backend/server.py`.
2. Abra `http://127.0.0.1:8765/admin/`.
3. Crie, altere ou exclua escolas.
4. O backend atualiza o banco e regrava:

- `public/data/schools/e_estaduais.json`
- `public/data/schools/e_municipais.json`
- `public/data/schools/e_federais.json`
- `public/data/schools/e_privadas.json`

## Como regenerar manualmente

O script legado continua disponivel para regeneracao manual a partir dos GeoJSONs externos:

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

1. Rodar `python3 backend/server.py`.
2. Validar o mapa em `http://127.0.0.1:8765/`.
3. Validar o painel em `http://127.0.0.1:8765/admin/`.
4. Confirmar se os quatro arquivos `e_*.json` refletem a mudanca.
5. Fazer commit das alteracoes quando quiser publicar no Pages.
