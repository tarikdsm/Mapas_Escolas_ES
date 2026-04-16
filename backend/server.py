#!/usr/bin/env python3
"""Servidor local do projeto com API CRUD, SQLite e publicacao estatica."""

from __future__ import annotations

import json
import hashlib
import mimetypes
import os
import sqlite3
import threading
import traceback
import unicodedata
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = PROJECT_ROOT / "public"
STATIC_CONFIG_PATH = PUBLIC_ROOT / "data" / "config" / "app-config.json"
DATABASE_PATH = PROJECT_ROOT / "backend" / "data" / "schools.sqlite3"
HOST = os.environ.get("ESCOLAS_HOST", "127.0.0.1")
PORT = int(os.environ.get("ESCOLAS_PORT", "8765"))
WRITE_LOCK = threading.Lock()
EXPORT_SCHEDULE_LOCK = threading.Lock()
MAX_REQUEST_BODY_BYTES = 262_144
EXPORT_DEBOUNCE_SECONDS = 0.5
EXPORT_TIMER: threading.Timer | None = None
EXPORT_GENERATION = 0
LOCAL_BIND_HOSTS = {"127.0.0.1", "localhost", "::1"}
SOURCE_OF_TRUTH = "sqlite"
SNAPSHOT_IMPORT_SOURCE = "static-snapshot-bootstrap"

NETWORKS = (
    {
        "id": "municipais",
        "dataset_name": "e_municipais",
        "label": "E. Municipais",
    },
    {
        "id": "estaduais",
        "dataset_name": "e_estaduais",
        "label": "E. Estaduais",
    },
    {
        "id": "federais",
        "dataset_name": "e_federais",
        "label": "E. Federais",
    },
    {
        "id": "privadas",
        "dataset_name": "e_privadas",
        "label": "E. Privadas",
    },
)
NETWORK_BY_ID = {item["id"]: item for item in NETWORKS}

SCHOOL_COLUMNS = (
    "id",
    "network_type",
    "inep_code",
    "name",
    "name_original",
    "municipio",
    "uf",
    "status",
    "address",
    "number",
    "complement",
    "district",
    "postal_code",
    "classification",
    "display_type",
    "institution",
    "acronym",
    "georef_source",
    "phone_primary",
    "email",
    "teacher_count",
    "student_count",
    "teacher_estimated",
    "student_estimated",
    "estimate_note",
    "notes",
    "latitude",
    "longitude",
    "detail_shard",
    "created_at",
    "updated_at",
)


class SchoolNotFoundError(LookupError):
    """Raised when an update/delete operation targets a missing school."""


def get_configured_host() -> str:
    return clean_text(os.environ.get("ESCOLAS_HOST", HOST)) or "127.0.0.1"


def get_configured_port() -> int:
    raw = clean_text(os.environ.get("ESCOLAS_PORT", str(PORT))) or str(PORT)
    try:
        return int(raw)
    except ValueError:
        return PORT


def is_local_bind_host(host: str) -> bool:
    return clean_text(host).lower() in LOCAL_BIND_HOSTS


def ensure_remote_bind_is_allowed(host: str) -> None:
    normalized = clean_text(host)
    if is_local_bind_host(normalized):
        return
    if clean_text(os.environ.get("ESCOLAS_ALLOW_REMOTE")) == "1":
        print(f"AVISO: bind remoto habilitado explicitamente em {normalized}.")
        return

    print(f"AVISO: bind remoto solicitado em {normalized}, mas ESCOLAS_ALLOW_REMOTE != 1.")
    raise SystemExit("Bind remoto bloqueado. Defina ESCOLAS_ALLOW_REMOTE=1 para continuar.")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    parts = []
    for chunk in text.replace("/", " ").replace("-", " ").split():
        normalized = "".join(character for character in chunk if character.isalnum())
        if normalized:
            parts.append(normalized)
    return "-".join(parts) or "sem-municipio"


def normalize_search_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", clean_text(value))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(text.split())


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "null", "undefined"}:
        return ""
    return text


def clean_int(value: Any) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return int(round(float(text.replace(",", "."))))
    except ValueError:
        return None


def clean_float(value: Any) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def build_export_address(record: dict[str, Any]) -> str:
    parts = []
    address = clean_text(record.get("address"))
    number = clean_text(record.get("number"))
    complement = clean_text(record.get("complement"))
    district = clean_text(record.get("district"))

    if address and number:
        parts.append(f"{address}, {number}")
    elif address:
        parts.append(address)
    elif number:
        parts.append(number)

    if complement and complement.lower() not in " ".join(parts).lower():
        parts.append(complement)
    if district and district.lower() not in " ".join(parts).lower():
        parts.append(district)

    return ", ".join(part for part in parts if part)


def frontend_record_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Nome_escola": row["name_original"] or row["name"],
        "Endereco": build_export_address(row),
        "Municipio": row["municipio"] or "",
        "CEP": row["postal_code"] or "",
        "telefone": row["phone_primary"] or "",
        "email": row["email"] or "",
        "Latitude": round(float(row["latitude"]), 6),
        "Longitude": round(float(row["longitude"]), 6),
        "Numero_professores": row["teacher_count"],
        "Numero_alunos": row["student_count"],
    }


def json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def path_is_within_root(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.create_function("normalize_text", 1, normalize_search_text)
    return connection


def set_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        """
        INSERT INTO meta(key, value)
        VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def get_meta(connection: sqlite3.Connection, key: str, default: str = "") -> str:
    row = connection.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    if not row:
        return default
    return str(row["value"])


def touch_data_version(connection: sqlite3.Connection) -> str:
    version = utc_now()
    set_meta(connection, "data_version", version)
    set_meta(connection, "updated_at", version)
    return version


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS schools (
            id TEXT PRIMARY KEY,
            network_type TEXT NOT NULL,
            inep_code TEXT,
            name TEXT NOT NULL,
            name_original TEXT,
            municipio TEXT NOT NULL,
            uf TEXT,
            status TEXT,
            address TEXT,
            number TEXT,
            complement TEXT,
            district TEXT,
            postal_code TEXT,
            classification TEXT,
            display_type TEXT,
            institution TEXT,
            acronym TEXT,
            georef_source TEXT,
            phone_primary TEXT,
            email TEXT,
            teacher_count INTEGER,
            student_count INTEGER,
            teacher_estimated TEXT,
            student_estimated TEXT,
            estimate_note TEXT,
            notes TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            detail_shard TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_schools_network_type
        ON schools(network_type);

        CREATE INDEX IF NOT EXISTS idx_schools_municipio
        ON schools(municipio);

        CREATE INDEX IF NOT EXISTS idx_schools_name
        ON schools(name);

        CREATE INDEX IF NOT EXISTS idx_schools_inep_code
        ON schools(inep_code);
        """
    )
    connection.commit()


def load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_frontend_school_records(
    dataset_name: str,
    public_root: Path | None = None,
) -> list[dict[str, Any]]:
    public_root = public_root or PUBLIC_ROOT
    dataset_path = public_root / "data" / "schools" / f"{dataset_name}.json"
    if not dataset_path.exists():
        return []

    payload = load_json_file(dataset_path)
    if not isinstance(payload, list):
        raise ValueError(f"Dataset invalido em {dataset_path}. Esperado: lista JSON.")

    records: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, dict):
            records.append(item)
    return records


def build_import_school_id(network_type: str, record: dict[str, Any], index: int) -> str:
    name = clean_text(record.get("Nome_escola")) or "escola"
    municipio = clean_text(record.get("Municipio"))
    address = clean_text(record.get("Endereco"))
    latitude = clean_text(record.get("Latitude"))
    longitude = clean_text(record.get("Longitude"))
    digest_input = "|".join(
        [network_type, name, municipio, address, latitude, longitude, str(index)]
    ).encode("utf-8")
    digest = hashlib.sha1(digest_input).hexdigest()[:10]
    return f"{network_type}_{slugify(name)[:48]}_{digest}"


def build_import_row_from_frontend_record(
    network_type: str,
    record: dict[str, Any],
    index: int,
    now: str,
) -> dict[str, Any] | None:
    latitude = clean_float(record.get("Latitude"))
    longitude = clean_float(record.get("Longitude"))
    if latitude is None or longitude is None:
        return None

    name = clean_text(record.get("Nome_escola")) or f"Escola {index + 1}"
    municipio = clean_text(record.get("Municipio"))
    postal_code = clean_text(record.get("CEP"))
    phone_primary = clean_text(record.get("telefone"))
    email = clean_text(record.get("email"))
    address = clean_text(record.get("Endereco"))
    detail_shard = slugify(municipio)

    return {
        "id": build_import_school_id(network_type, record, index),
        "network_type": network_type,
        "inep_code": "",
        "name": name,
        "name_original": name,
        "municipio": municipio or "Sem municipio",
        "uf": "ES",
        "status": "",
        "address": address,
        "number": "",
        "complement": "",
        "district": "",
        "postal_code": postal_code,
        "classification": "",
        "display_type": "",
        "institution": "",
        "acronym": "",
        "georef_source": SNAPSHOT_IMPORT_SOURCE,
        "phone_primary": phone_primary,
        "email": email,
        "teacher_count": clean_int(record.get("Numero_professores")),
        "student_count": clean_int(record.get("Numero_alunos")),
        "teacher_estimated": "",
        "student_estimated": "",
        "estimate_note": "",
        "notes": "",
        "latitude": latitude,
        "longitude": longitude,
        "detail_shard": detail_shard,
        "created_at": now,
        "updated_at": now,
    }


def build_import_rows(public_root: Path | None = None) -> list[dict[str, Any]]:
    public_root = public_root or PUBLIC_ROOT
    now = utc_now()
    rows: list[dict[str, Any]] = []

    for network in NETWORKS:
        records = load_frontend_school_records(network["dataset_name"], public_root=public_root)
        for index, record in enumerate(records):
            normalized = build_import_row_from_frontend_record(network["id"], record, index, now)
            if normalized is not None:
                rows.append(normalized)

    rows.sort(key=lambda item: (item["network_type"], item["municipio"], item["name"], item["id"]))
    return rows


def import_static_school_data(
    connection: sqlite3.Connection,
    public_root: Path | None = None,
) -> None:
    public_root = public_root or PUBLIC_ROOT
    rows = build_import_rows(public_root=public_root)
    if not rows:
        raise RuntimeError("Nao foi possivel importar nenhuma escola da base estatica atual.")

    columns_sql = ", ".join(SCHOOL_COLUMNS)
    placeholders = ", ".join("?" for _ in SCHOOL_COLUMNS)
    connection.execute("DELETE FROM schools")
    connection.executemany(
        f"INSERT INTO schools ({columns_sql}) VALUES ({placeholders})",
        [tuple(row[column] for column in SCHOOL_COLUMNS) for row in rows],
    )
    touch_data_version(connection)
    connection.commit()


def fetch_rows(
    connection: sqlite3.Connection,
    query: str,
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    return [row_to_dict(row) for row in connection.execute(query, params).fetchall()]


def fetch_school_by_id(connection: sqlite3.Connection, school_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        f"SELECT {', '.join(SCHOOL_COLUMNS)} FROM schools WHERE id = ?",
        (school_id,),
    ).fetchone()
    if not row:
        return None
    return row_to_dict(row)


def list_frontend_dataset(connection: sqlite3.Connection, network_type: str) -> list[dict[str, Any]]:
    rows = fetch_rows(
        connection,
        f"""
        SELECT {', '.join(SCHOOL_COLUMNS)}
        FROM schools
        WHERE network_type = ?
        ORDER BY municipio COLLATE NOCASE, name COLLATE NOCASE, address COLLATE NOCASE, id
        """,
        (network_type,),
    )
    return [frontend_record_from_row(row) for row in rows]


def write_static_exports(connection: sqlite3.Connection) -> None:
    for network in NETWORKS:
        output_path = PUBLIC_ROOT / "data" / "schools" / f"{network['dataset_name']}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(json_bytes(list_frontend_dataset(connection, network["id"])))


def flush_static_exports(
    connection_factory: Any | None = None,
    exporter: Any | None = None,
) -> None:
    connection_factory = connection_factory or get_connection
    exporter = exporter or write_static_exports

    with WRITE_LOCK:
        connection = connection_factory()
        try:
            exporter(connection)
        finally:
            connection.close()


def _run_scheduled_export_flush(generation: int) -> None:
    global EXPORT_TIMER

    with EXPORT_SCHEDULE_LOCK:
        if generation != EXPORT_GENERATION:
            return
        EXPORT_TIMER = None

    try:
        flush_static_exports()
    except Exception as error:  # pragma: no cover - fallback operacional
        print(f"Erro ao regravar exports estaticos: {error}")
        traceback.print_exc()


def schedule_static_exports_flush(delay_seconds: float | None = None) -> None:
    global EXPORT_TIMER, EXPORT_GENERATION

    delay_seconds = EXPORT_DEBOUNCE_SECONDS if delay_seconds is None else delay_seconds
    with EXPORT_SCHEDULE_LOCK:
        EXPORT_GENERATION += 1
        generation = EXPORT_GENERATION
        if EXPORT_TIMER is not None:
            EXPORT_TIMER.cancel()

        timer = threading.Timer(delay_seconds, _run_scheduled_export_flush, args=(generation,))
        timer.daemon = True
        EXPORT_TIMER = timer
        timer.start()


def cancel_scheduled_export_flush() -> None:
    global EXPORT_TIMER, EXPORT_GENERATION

    with EXPORT_SCHEDULE_LOCK:
        EXPORT_GENERATION += 1
        timer = EXPORT_TIMER
        EXPORT_TIMER = None

    if timer is not None:
        timer.cancel()


def flush_scheduled_export_flush() -> None:
    cancel_scheduled_export_flush()
    flush_static_exports()


def validate_network_type(network_type: str) -> str:
    normalized = clean_text(network_type)
    if normalized not in NETWORK_BY_ID:
        raise ValueError("network_type invalido.")
    return normalized


def normalize_school_payload(payload: dict[str, Any], existing_id: str | None = None) -> dict[str, Any]:
    network_type = validate_network_type(payload.get("network_type"))
    name = clean_text(payload.get("name"))
    municipio = clean_text(payload.get("municipio"))
    latitude = clean_float(payload.get("latitude"))
    longitude = clean_float(payload.get("longitude"))

    if not name:
        raise ValueError("name e obrigatorio.")
    if not municipio:
        raise ValueError("municipio e obrigatorio.")
    if latitude is None or longitude is None:
        raise ValueError("latitude e longitude validas sao obrigatorias.")

    school_id = clean_text(payload.get("id")) or existing_id
    if not school_id:
        school_id = f"{network_type}_{slugify(name)}_{uuid.uuid4().hex[:10]}"

    now = utc_now()
    created_at = clean_text(payload.get("created_at")) or now

    normalized = {
        "id": school_id,
        "network_type": network_type,
        "inep_code": clean_text(payload.get("inep_code")),
        "name": name,
        "name_original": clean_text(payload.get("name_original")) or name,
        "municipio": municipio,
        "uf": clean_text(payload.get("uf")) or "ES",
        "status": clean_text(payload.get("status")),
        "address": clean_text(payload.get("address")),
        "number": clean_text(payload.get("number")),
        "complement": clean_text(payload.get("complement")),
        "district": clean_text(payload.get("district")),
        "postal_code": clean_text(payload.get("postal_code")),
        "classification": clean_text(payload.get("classification")),
        "display_type": clean_text(payload.get("display_type")),
        "institution": clean_text(payload.get("institution")),
        "acronym": clean_text(payload.get("acronym")),
        "georef_source": clean_text(payload.get("georef_source")),
        "phone_primary": clean_text(payload.get("phone_primary")),
        "email": clean_text(payload.get("email")),
        "teacher_count": clean_int(payload.get("teacher_count")),
        "student_count": clean_int(payload.get("student_count")),
        "teacher_estimated": clean_text(payload.get("teacher_estimated")),
        "student_estimated": clean_text(payload.get("student_estimated")),
        "estimate_note": clean_text(payload.get("estimate_note")),
        "notes": clean_text(payload.get("notes")),
        "latitude": latitude,
        "longitude": longitude,
        "detail_shard": clean_text(payload.get("detail_shard")) or slugify(municipio),
        "created_at": created_at,
        "updated_at": now,
    }
    return normalized


def upsert_school(
    payload: dict[str, Any],
    school_id: str | None = None,
    *,
    require_existing: bool = False,
    connection_factory: Any = get_connection,
) -> dict[str, Any]:
    with WRITE_LOCK:
        connection = connection_factory()
        try:
            existing = fetch_school_by_id(connection, school_id) if school_id else None
            if require_existing and school_id and existing is None:
                raise SchoolNotFoundError("Escola nao encontrada.")
            normalized = normalize_school_payload(payload, existing_id=school_id)

            if existing is None:
                duplicate = fetch_school_by_id(connection, normalized["id"])
                if duplicate:
                    raise ValueError("Ja existe uma escola com este id.")
                connection.execute(
                    f"""
                    INSERT INTO schools ({', '.join(SCHOOL_COLUMNS)})
                    VALUES ({', '.join('?' for _ in SCHOOL_COLUMNS)})
                    """,
                    tuple(normalized[column] for column in SCHOOL_COLUMNS),
                )
            else:
                normalized["created_at"] = existing["created_at"]
                normalized["id"] = existing["id"]
                connection.execute(
                    f"""
                    UPDATE schools
                    SET {', '.join(f"{column} = ?" for column in SCHOOL_COLUMNS if column != 'id')}
                    WHERE id = ?
                    """,
                    tuple(
                        normalized[column]
                        for column in SCHOOL_COLUMNS
                        if column != "id"
                    )
                    + (existing["id"],),
                )

            touch_data_version(connection)
            connection.commit()
            saved = fetch_school_by_id(connection, normalized["id"])
            if saved is None:
                raise RuntimeError("Falha ao recarregar a escola salva.")
            schedule_static_exports_flush()
            return saved
        finally:
            connection.close()


def delete_school(school_id: str, connection_factory: Any = get_connection) -> bool:
    with WRITE_LOCK:
        connection = connection_factory()
        try:
            cursor = connection.execute("DELETE FROM schools WHERE id = ?", (school_id,))
            if cursor.rowcount <= 0:
                connection.rollback()
                return False
            touch_data_version(connection)
            connection.commit()
            schedule_static_exports_flush()
            return True
        finally:
            connection.close()


def build_runtime_config(
    base_url: str,
    *,
    config_loader: Any = load_json_file,
    connection_factory: Any = get_connection,
) -> dict[str, Any]:
    config = config_loader(STATIC_CONFIG_PATH)
    connection = connection_factory()
    try:
        version = get_meta(connection, "data_version", "")
    finally:
        connection.close()

    for layer in config.get("schoolLayers", []):
        layer["dataPath"] = f"/api/frontend/schools/{layer['id']}"

    config["runtime"] = {
        "apiEnabled": True,
        "dataVersion": version,
        "frontendUrl": "/",
        "adminUrl": "/admin/",
        "apiBaseUrl": f"{base_url}/api",
    }
    return config


def parse_limit(value: str, default: int = 50, maximum: int = 500) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def parse_offset(value: str, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


def build_school_list_response(
    query_params: dict[str, list[str]],
    connection_factory: Any = get_connection,
) -> dict[str, Any]:
    connection = connection_factory()
    try:
        network_type = clean_text((query_params.get("network_type") or [""])[0])
        municipio = clean_text((query_params.get("municipio") or [""])[0])
        search = clean_text((query_params.get("q") or [""])[0])
        limit = parse_limit((query_params.get("limit") or ["50"])[0])
        offset = parse_offset((query_params.get("offset") or ["0"])[0])

        where_clauses = []
        params: list[Any] = []

        if network_type:
            where_clauses.append("network_type = ?")
            params.append(validate_network_type(network_type))
        if municipio:
            where_clauses.append("normalize_text(municipio) = normalize_text(?)")
            params.append(municipio)
        if search:
            where_clauses.append(
                "("
                "normalize_text(name) LIKE normalize_text(?) OR "
                "normalize_text(name_original) LIKE normalize_text(?) OR "
                "normalize_text(municipio) LIKE normalize_text(?) OR "
                "normalize_text(inep_code) LIKE normalize_text(?)"
                ")"
            )
            like = f"%{search}%"
            params.extend([like, like, like, like])

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        total = connection.execute(
            f"SELECT COUNT(*) AS total FROM schools {where_sql}",
            tuple(params),
        ).fetchone()["total"]
        items = fetch_rows(
            connection,
            f"""
            SELECT {', '.join(SCHOOL_COLUMNS)}
            FROM schools
            {where_sql}
            ORDER BY municipio COLLATE NOCASE, name COLLATE NOCASE, id
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        )
        return {
            "items": items,
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }
    finally:
        connection.close()


def build_options_response(connection_factory: Any = get_connection) -> dict[str, Any]:
    connection = connection_factory()
    try:
        municipality_variants: dict[str, str] = {}
        for row in connection.execute(
            """
            SELECT municipio
            FROM schools
            GROUP BY municipio
            ORDER BY municipio COLLATE NOCASE
            """
        ).fetchall():
            municipio = clean_text(row["municipio"])
            if not municipio:
                continue
            normalized = normalize_search_text(municipio)
            current = municipality_variants.get(normalized)
            if current is None:
                municipality_variants[normalized] = municipio
                continue
            candidate_score = (sum(1 for char in municipio if ord(char) > 127), len(municipio))
            current_score = (sum(1 for char in current if ord(char) > 127), len(current))
            if candidate_score > current_score:
                municipality_variants[normalized] = municipio

        municipios = sorted(municipality_variants.values(), key=lambda item: normalize_search_text(item))
        counts = fetch_rows(
            connection,
            """
            SELECT network_type, COUNT(*) AS school_count
            FROM schools
            GROUP BY network_type
            ORDER BY network_type
            """,
        )
        return {
            "networkTypes": [
                {
                    "id": item["id"],
                    "label": item["label"],
                    "schoolCount": next(
                        (
                            count["school_count"]
                            for count in counts
                            if count["network_type"] == item["id"]
                        ),
                        0,
                    ),
                }
                for item in NETWORKS
            ],
            "municipios": municipios,
        }
    finally:
        connection.close()


def build_meta_response(connection_factory: Any = get_connection) -> dict[str, Any]:
    connection = connection_factory()
    try:
        total = connection.execute("SELECT COUNT(*) AS total FROM schools").fetchone()["total"]
        return {
            "status": "ok",
            "sourceOfTruth": SOURCE_OF_TRUTH,
            "snapshotExportsEnabled": True,
            "dataVersion": get_meta(connection, "data_version", ""),
            "updatedAt": get_meta(connection, "updated_at", ""),
            "schoolCount": int(total),
            "frontendUrl": "/",
            "adminUrl": "/admin/",
        }
    finally:
        connection.close()


def build_etag(value: str) -> str:
    text = clean_text(value).replace('"', "")
    return f'"{text}"'


def etag_matches(header_value: str, expected_etag: str) -> bool:
    candidates = [item.strip() for item in clean_text(header_value).split(",") if item.strip()]
    return "*" in candidates or expected_etag in candidates


def ensure_database_ready(
    connection_factory: Any = get_connection,
    importer: Any = import_static_school_data,
) -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = connection_factory()
    try:
        create_schema(connection)
        count = connection.execute("SELECT COUNT(*) AS total FROM schools").fetchone()["total"]
        if int(count) == 0:
            importer(connection, public_root=PUBLIC_ROOT)
    finally:
        connection.close()


class EscolasRequestHandler(BaseHTTPRequestHandler):
    server_version = "EscolasES/1.0"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_default_headers("application/json; charset=utf-8")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/health":
                self._send_json({"status": "ok"})
                return

            if path == "/api/meta":
                meta = build_meta_response()
                etag = build_etag(meta.get("dataVersion", ""))
                if etag_matches(self.headers.get("If-None-Match", ""), etag):
                    self._send_status(HTTPStatus.NOT_MODIFIED, extra_headers={"ETag": etag})
                    return
                self._send_json(meta, extra_headers={"ETag": etag})
                return

            if path == "/api/options":
                self._send_json(build_options_response())
                return

            if path == "/api/config":
                base_url = f"http://{self.headers.get('Host', f'{get_configured_host()}:{get_configured_port()}')}"
                self._send_json(build_runtime_config(base_url))
                return

            if path.startswith("/api/frontend/schools/"):
                layer_id = clean_text(path.rsplit("/", 1)[-1])
                if layer_id not in NETWORK_BY_ID:
                    self._send_json({"error": "Camada nao encontrada."}, status=HTTPStatus.NOT_FOUND)
                    return
                connection = get_connection()
                try:
                    self._send_json(list_frontend_dataset(connection, layer_id))
                finally:
                    connection.close()
                return

            if path == "/api/schools":
                self._send_json(build_school_list_response(parse_qs(parsed.query)))
                return

            if path.startswith("/api/schools/"):
                school_id = unquote(path[len("/api/schools/") :])
                connection = get_connection()
                try:
                    school = fetch_school_by_id(connection, school_id)
                finally:
                    connection.close()
                if school is None:
                    self._send_json({"error": "Escola nao encontrada."}, status=HTTPStatus.NOT_FOUND)
                    return
                self._send_json(school)
                return

            self._serve_static(path)
        except ValueError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as error:  # pragma: no cover - fallback operacional
            print(f"Erro interno em GET {self.path}: {error}")
            traceback.print_exc()
            self._send_json(
                {"error": "Falha interna no servidor."},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not self._is_mutation_request_allowed():
            return

        if parsed.path == "/api/exports/flush":
            try:
                flush_scheduled_export_flush()
                self._send_json({"flushed": True})
            except Exception as error:  # pragma: no cover - fallback operacional
                print(f"Erro interno em POST {self.path}: {error}")
                traceback.print_exc()
                self._send_json(
                    {"error": "Falha ao regravar exports estaticos."},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if parsed.path != "/api/schools":
            self._send_json({"error": "Rota nao encontrada."}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self._read_json_body()
            saved = upsert_school(payload)
            self._send_json(saved, status=HTTPStatus.CREATED)
        except ValueError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as error:  # pragma: no cover - fallback operacional
            print(f"Erro interno em POST {self.path}: {error}")
            traceback.print_exc()
            self._send_json(
                {"error": "Falha ao criar escola."},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        if not self._is_mutation_request_allowed():
            return

        if not parsed.path.startswith("/api/schools/"):
            self._send_json({"error": "Rota nao encontrada."}, status=HTTPStatus.NOT_FOUND)
            return

        school_id = unquote(parsed.path[len("/api/schools/") :])
        try:
            payload = self._read_json_body()
            saved = upsert_school(payload, school_id=school_id, require_existing=True)
            self._send_json(saved)
        except SchoolNotFoundError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.NOT_FOUND)
        except ValueError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as error:  # pragma: no cover - fallback operacional
            print(f"Erro interno em PUT {self.path}: {error}")
            traceback.print_exc()
            self._send_json(
                {"error": "Falha ao atualizar escola."},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if not self._is_mutation_request_allowed():
            return

        if not parsed.path.startswith("/api/schools/"):
            self._send_json({"error": "Rota nao encontrada."}, status=HTTPStatus.NOT_FOUND)
            return

        school_id = unquote(parsed.path[len("/api/schools/") :])
        try:
            deleted = delete_school(school_id)
            if not deleted:
                self._send_json({"error": "Escola nao encontrada."}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json({"deleted": True, "id": school_id})
        except Exception as error:  # pragma: no cover - fallback operacional
            print(f"Erro interno em DELETE {self.path}: {error}")
            traceback.print_exc()
            self._send_json(
                {"error": "Falha ao excluir escola."},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def log_message(self, format: str, *args: Any) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = format % args
        print(f"[{timestamp}] {self.address_string()} {message}")

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > MAX_REQUEST_BODY_BYTES:
            self._discard_request_body(length)
            raise ValueError("Corpo da requisicao excede o limite permitido.")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError("JSON invalido.") from error
        if not isinstance(payload, dict):
            raise ValueError("O corpo precisa ser um objeto JSON.")
        return payload

    def _discard_request_body(self, length: int) -> None:
        remaining = max(0, length)
        while remaining > 0:
            chunk = self.rfile.read(min(65_536, remaining))
            if not chunk:
                break
            remaining -= len(chunk)

    def _default_request_port(self) -> int:
        return int(self.server.server_address[1])

    def _parse_host_header(self) -> tuple[str, int | None]:
        raw_host = clean_text(self.headers.get("Host"))
        if not raw_host:
            return "", None

        parsed = urlparse(f"//{raw_host}")
        hostname = clean_text(parsed.hostname).lower()
        port = parsed.port or self._default_request_port()
        return hostname, port

    def _parse_origin(self) -> tuple[str, int | None] | None:
        raw_origin = clean_text(self.headers.get("Origin"))
        if not raw_origin:
            return None

        parsed = urlparse(raw_origin)
        hostname = clean_text(parsed.hostname).lower()
        if not hostname:
            return None

        if parsed.port is not None:
            port = parsed.port
        elif parsed.scheme == "https":
            port = 443
        else:
            port = 80
        return hostname, port

    def _hosts_match(self, left: str, right: str) -> bool:
        if left == right:
            return True
        return left in LOCAL_BIND_HOSTS and right in LOCAL_BIND_HOSTS

    def _origin_matches_request_host(self) -> bool:
        origin = self._parse_origin()
        if origin is None:
            return False

        request_host, request_port = self._parse_host_header()
        if not request_host or request_port is None:
            return False

        origin_host, origin_port = origin
        return self._hosts_match(origin_host, request_host) and origin_port == request_port

    def _is_mutation_request_allowed(self) -> bool:
        origin = clean_text(self.headers.get("Origin"))
        if not origin:
            return True
        if self._origin_matches_request_host():
            return True

        self._send_json(
            {"error": "Origem nao autorizada para operacoes de escrita."},
            status=HTTPStatus.FORBIDDEN,
        )
        return False

    def _get_cors_allow_origin(self) -> str | None:
        if self.command == "GET":
            return "*"

        if self.command in {"POST", "PUT", "DELETE", "OPTIONS"} and self._origin_matches_request_host():
            return clean_text(self.headers.get("Origin"))

        return None

    def _send_default_headers(
        self,
        content_type: str,
        content_length: int | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        allow_origin = self._get_cors_allow_origin()
        if allow_origin:
            self.send_header("Access-Control-Allow-Origin", allow_origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Vary", "Origin")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        if content_length is not None:
            self.send_header("Content-Length", str(content_length))

    def _send_status(
        self,
        status: HTTPStatus,
        *,
        content_type: str = "application/json; charset=utf-8",
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self._send_default_headers(content_type, 0, extra_headers=extra_headers)
        self.end_headers()

    def _send_json(
        self,
        payload: Any,
        status: HTTPStatus = HTTPStatus.OK,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self._send_default_headers(
            "application/json; charset=utf-8",
            len(body),
            extra_headers=extra_headers,
        )
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path: str) -> None:
        normalized_path = path or "/"
        if normalized_path == "/admin":
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", "/admin/")
            self.end_headers()
            return

        if normalized_path == "/":
            target = PUBLIC_ROOT / "index.html"
        elif normalized_path == "/admin/":
            target = PUBLIC_ROOT / "admin" / "index.html"
        else:
            relative_path = normalized_path.lstrip("/")
            target = (PUBLIC_ROOT / relative_path).resolve()
            if not path_is_within_root(PUBLIC_ROOT.resolve(), target):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            if target.is_dir():
                target = target / "index.html"

        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {
            "application/javascript",
            "application/json",
            "image/svg+xml",
        }:
            content_type += "; charset=utf-8"

        self.send_response(HTTPStatus.OK)
        self._send_default_headers(content_type, len(content))
        self.end_headers()
        self.wfile.write(content)


def main() -> int:
    host = get_configured_host()
    port = get_configured_port()
    ensure_remote_bind_is_allowed(host)
    ensure_database_ready()
    server = ThreadingHTTPServer((host, port), EscolasRequestHandler)
    print(f"Servidor iniciado em http://{host}:{port}")
    print(f"Mapa: http://{host}:{port}/")
    print(f"Painel administrativo: http://{host}:{port}/admin/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        cancel_scheduled_export_flush()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
