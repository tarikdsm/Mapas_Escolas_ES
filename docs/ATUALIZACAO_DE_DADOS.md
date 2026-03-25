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

## Fluxo para o contorno do estado

Use a malha oficial dos municipios do ES para recompor o contorno externo do estado:

```bash
python scripts/build_state_boundary.py \
  --input "/caminho/para/ibge_municipios_es.geojson" \
  --output "data/boundaries/es_state.geojson"
```

Esse passo corrige trechos costeiros em que um poligono estadual simplificado pode deixar escolas visualmente fora da area util do mapa.

Se houver escolas muito proximas da costa ou da divisa ainda encostando na borda visual, ajuste `stateBoundary.bufferDegrees` em `data/config/app-config.json`.

## Checklist antes do commit

1. Validar se o GeoJSON abre sem erro.
2. Confirmar contagem de registros da camada.
3. Confirmar que `app-config.json` aponta para os arquivos corretos.
4. Abrir o site localmente e testar os toggles.
5. Commitar os artefatos gerados junto com a atualização da documentação, se houver mudança de fonte ou contrato.
