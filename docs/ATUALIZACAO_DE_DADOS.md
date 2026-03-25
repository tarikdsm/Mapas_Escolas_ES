# Atualização de Dados

## Visão geral

O site foi estruturado para aceitar novas bases sem mudanças profundas na interface. As camadas do mapa são controladas por `data/config/app-config.json`, enquanto os dados são mantidos em `data/schools/` e `data/density/`.

## Fluxo para escolas

### 1. Obter a base bruta

Use o GeoJSON consolidado e georreferenciado da rede correspondente.

### 2. Normalizar para o contrato do site

Exemplo para a rede estadual:

```bash
python scripts/build_school_layer.py \
  --input "/caminho/origem/escolas_estaduais_es_georef.geojson" \
  --output "data/schools/estaduais.geojson" \
  --layer-id "estaduais" \
  --label "E. Estaduais" \
  --color "#2563eb"
```

### 3. Ativar a camada no mapa

Edite `data/config/app-config.json`:

- troque `status` para `ready`
- ajuste `defaultVisible` conforme a estratégia de publicação

## Fluxo para densidade populacional

```bash
python scripts/build_density_layer.py \
  --output "data/density/es_municipios_density.geojson"
```

## Checklist antes do commit

1. Validar se o GeoJSON abre sem erro.
2. Confirmar contagem de registros da camada.
3. Confirmar que `app-config.json` aponta para os arquivos corretos.
4. Abrir o site localmente e testar os toggles.
5. Commitar os artefatos gerados junto com a atualização da documentação, se houver mudança de fonte ou contrato.

