# API do Backend

## Visao geral

Backend local em Python com SQLite unico para todas as escolas.

O SQLite e a fonte de verdade do modo local. Se o banco ainda nao existir, a primeira carga pode usar os snapshots versionados em `public/data/schools/e_*.json` apenas como bootstrap de recuperacao.

Base local padrao:

- servidor: `http://127.0.0.1:8765`
- mapa: `/`
- painel: `/admin/`
- API: `/api/`

O mapa local tenta `GET /api/config` antes do fallback estatico.

Seguranca operacional atual:

- bind remoto bloqueado por padrao; para subir com `ESCOLAS_HOST` fora de `127.0.0.1`/`localhost`/`::1`, e obrigatorio definir `ESCOLAS_ALLOW_REMOTE=1`
- CORS aberto apenas para leituras `GET`
- rotas mutantes (`POST`, `PUT`, `DELETE`) aceitam `Origin` apenas quando ela bate com o `Host` da requisicao

Isso reduz exposicao acidental e bloqueia escrita cross-origin em navegador, mas nao substitui autenticacao. Para hospedagem publica na AWS, o recomendado e colocar as rotas de escrita atras de autenticao e/ou rede privada.

## Limite do GitHub Pages

O GitHub Pages publica apenas `public/`.

Por isso:

- o mapa publicado funciona com snapshot estatico
- o painel publicado entra em modo somente leitura
- CRUD, banco SQLite e API com escrita funcionam localmente

## Modelo principal

Cada escola fica em uma linha unica no SQLite com estes campos:

- `id`
- `network_type`
- `inep_code`
- `name`
- `name_original`
- `municipio`
- `uf`
- `status`
- `address`
- `number`
- `complement`
- `district`
- `postal_code`
- `classification`
- `display_type`
- `institution`
- `acronym`
- `georef_source`
- `phone_primary`
- `email`
- `teacher_count`
- `student_count`
- `teacher_estimated`
- `student_estimated`
- `estimate_note`
- `notes`
- `latitude`
- `longitude`
- `detail_shard`
- `created_at`
- `updated_at`

Redes validas em `network_type`:

- `municipais`
- `estaduais`
- `federais`
- `privadas`

## Endpoints

### `GET /api/health`

Resposta:

```json
{
  "status": "ok"
}
```

### `GET /api/meta`

Usado pelo frontend local para detectar mudancas e recarregar as camadas.

Inclui `ETag` baseado em `dataVersion`.

Se a requisicao enviar `If-None-Match` com o mesmo valor atual, o backend responde `304 Not Modified` sem corpo.

Resposta:

```json
{
  "status": "ok",
  "sourceOfTruth": "sqlite",
  "snapshotExportsEnabled": true,
  "dataVersion": "2026-04-15T14:58:34.082+00:00",
  "updatedAt": "2026-04-15T14:58:34.082+00:00",
  "schoolCount": 3493,
  "frontendUrl": "/",
  "adminUrl": "/admin/"
}
```

### `GET /api/config`

Entrega a configuracao do mapa em modo local, com os `dataPath` apontando para a API.

### `GET /api/options`

Usado pelo painel para popular filtros e seletores.

Resposta:

```json
{
  "networkTypes": [
    {
      "id": "municipais",
      "label": "E. Municipais",
      "schoolCount": 2226
    }
  ],
  "municipios": [
    "Afonso Cláudio",
    "Água Doce do Norte"
  ]
}
```

### `GET /api/frontend/schools/:layerId`

Fornece ao mapa o mesmo contrato leve que ele ja usa no frontend.

`layerId` aceitos:

- `municipais`
- `estaduais`
- `federais`
- `privadas`

Resposta:

```json
[
  {
    "Nome_escola": "EEEM - SÃO FRANCISCO",
    "Endereco": "RUA PEDRO RIBEIRO, 177, SAO FRANCISCO",
    "Municipio": "Afonso Claudio",
    "CEP": "29600-000",
    "telefone": "",
    "email": "escolasaofrancisco@sedu.es.gov.br",
    "Latitude": -19.997485,
    "Longitude": -41.134055,
    "Numero_professores": null,
    "Numero_alunos": null
  }
]
```

### `GET /api/schools`

Lista paginada para o painel.

Query params opcionais:

- `q`
- `network_type`
- `municipio`
- `limit`
- `offset`

Exemplo:

```text
/api/schools?q=vitoria&network_type=estaduais&limit=50&offset=0
```

Resposta:

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

### `GET /api/schools/:id`

Retorna todos os campos da escola.

### `POST /api/schools`

Cria uma escola.

Se a requisicao vier de um navegador com `Origin`, a escrita so e aceita quando a origem bate com o `Host` atual. Caso contrario, o backend retorna `403`.

Campos obrigatorios:

- `network_type`
- `name`
- `municipio`
- `latitude`
- `longitude`

Exemplo:

```json
{
  "network_type": "municipais",
  "name": "Escola Exemplo",
  "municipio": "Vitória",
  "uf": "ES",
  "latitude": -20.3155,
  "longitude": -40.3128
}
```

Ao salvar, o backend:

1. grava no SQLite
2. atualiza `dataVersion`
3. agenda a regravacao dos arquivos `public/data/schools/e_*.json` com debounce de 500 ms

Os `e_*.json` nao sao a base editavel. Eles sao snapshots gerados a partir do SQLite para publicacao e fallback estatico.

### `PUT /api/schools/:id`

Atualiza uma escola existente. O corpo segue o mesmo contrato do `POST`.

Se o `:id` nao existir, o backend retorna `404` e nao cria um novo registro.

### `DELETE /api/schools/:id`

Exclui uma escola, confirma a mudanca no SQLite e agenda a atualizacao dos exports estaticos.

Resposta:

```json
{
  "deleted": true,
  "id": "municipais_escola-exemplo_1234567890"
}
```

### `POST /api/exports/flush`

Forca imediatamente a regravacao dos arquivos `public/data/schools/e_*.json`.

Use quando for necessario garantir que os snapshots estaticos ja estejam atualizados antes de validar arquivos no disco, empacotar artefatos ou fazer commit manual.

Esta rota segue a mesma regra de seguranca das outras escritas: `Origin` externa recebe `403`.

Resposta:

```json
{
  "flushed": true
}
```

## Sincronizacao com o mapa

No modo local:

1. o mapa carrega configuracao de `/api/config`
2. as camadas escolares leem `/api/frontend/schools/:layerId`
3. o frontend faz polling de `/api/meta`
4. quando `dataVersion` muda, ele recarrega as camadas ativas

O SQLite continua sendo atualizado de forma sincronizada a cada mutacao. Apenas a exportacao dos `e_*.json` fica debounceada para reduzir regravacoes repetidas em edicoes em lote.

Quando nada muda, o frontend reutiliza `ETag` e recebe `304 Not Modified`, reduzindo o trafego do polling de 15 em 15 segundos.

## Publicacao

Depois de editar localmente:

1. aguarde o debounce terminar ou chame `POST /api/exports/flush`
2. confira os arquivos `public/data/schools/e_*.json`
3. faça commit dessas alteracoes
4. envie para o GitHub
5. o Pages publica o novo snapshot estatico
