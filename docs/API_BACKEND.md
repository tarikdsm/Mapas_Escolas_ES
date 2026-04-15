# API do Backend

## Visao geral

Backend local em Python com SQLite unico para todas as escolas.

Na primeira carga, o banco e inicializado a partir dos snapshots versionados em `public/data/schools/e_*.json`.

Base local padrao:

- servidor: `http://127.0.0.1:8765`
- mapa: `/`
- painel: `/admin/`
- API: `/api/`

O mapa local tenta `GET /api/config` antes do fallback estatico.

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

Resposta:

```json
{
  "status": "ok",
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
3. regrava os arquivos `public/data/schools/e_*.json`

### `PUT /api/schools/:id`

Atualiza uma escola existente. O corpo segue o mesmo contrato do `POST`.

### `DELETE /api/schools/:id`

Exclui uma escola e regrava os exports estaticos.

Resposta:

```json
{
  "deleted": true,
  "id": "municipais_escola-exemplo_1234567890"
}
```

## Sincronizacao com o mapa

No modo local:

1. o mapa carrega configuracao de `/api/config`
2. as camadas escolares leem `/api/frontend/schools/:layerId`
3. o frontend faz polling de `/api/meta`
4. quando `dataVersion` muda, ele recarrega as camadas ativas

## Publicacao

Depois de editar localmente:

1. confira os arquivos `public/data/schools/e_*.json`
2. faça commit dessas alteracoes
3. envie para o GitHub
4. o Pages publica o novo snapshot estatico
