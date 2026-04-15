"""Infraestrutura compartilhada para os testes automatizados do projeto."""

from __future__ import annotations

import http.client
import json
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend.server as backend_server

FIXTURE_ROWS = [
    {
        "id": "municipais_escola-sol",
        "network_type": "municipais",
        "inep_code": "1001",
        "name": "Escola Sol",
        "name_original": "Escola Sol",
        "municipio": "Vitória",
        "uf": "ES",
        "status": "Em Atividade",
        "address": "Rua do Sol",
        "number": "100",
        "complement": "",
        "district": "Centro",
        "postal_code": "29000-000",
        "classification": "alta",
        "display_type": "",
        "institution": "",
        "acronym": "",
        "georef_source": "teste",
        "phone_primary": "(27) 3000-0001",
        "email": "sol@example.com",
        "teacher_count": 12,
        "student_count": 300,
        "teacher_estimated": "",
        "student_estimated": "",
        "estimate_note": "",
        "notes": "",
        "latitude": -20.3155,
        "longitude": -40.3128,
        "detail_shard": "vitoria",
    },
    {
        "id": "estaduais_escola-lua",
        "network_type": "estaduais",
        "inep_code": "2002",
        "name": "Escola Lua",
        "name_original": "Escola Lua",
        "municipio": "Vitoria",
        "uf": "ES",
        "status": "Em Atividade",
        "address": "Avenida Mar",
        "number": "45",
        "complement": "",
        "district": "Praia",
        "postal_code": "29010-000",
        "classification": "media",
        "display_type": "",
        "institution": "",
        "acronym": "",
        "georef_source": "teste",
        "phone_primary": "(27) 3000-0002",
        "email": "lua@example.com",
        "teacher_count": 18,
        "student_count": 450,
        "teacher_estimated": "",
        "student_estimated": "",
        "estimate_note": "",
        "notes": "",
        "latitude": -20.3001,
        "longitude": -40.2954,
        "detail_shard": "vitoria",
    },
    {
        "id": "federais_escola-estrela",
        "network_type": "federais",
        "inep_code": "3003",
        "name": "Escola Estrela",
        "name_original": "Escola Estrela",
        "municipio": "Serra",
        "uf": "ES",
        "status": "Em Atividade",
        "address": "Rua das Flores",
        "number": "7",
        "complement": "",
        "district": "Jardim",
        "postal_code": "29160-000",
        "classification": "alta",
        "display_type": "Campus",
        "institution": "Instituto Federal",
        "acronym": "IF",
        "georef_source": "teste",
        "phone_primary": "(27) 3000-0003",
        "email": "estrela@example.com",
        "teacher_count": 30,
        "student_count": 700,
        "teacher_estimated": "",
        "student_estimated": "",
        "estimate_note": "",
        "notes": "",
        "latitude": -20.1987,
        "longitude": -40.2684,
        "detail_shard": "serra",
    },
]


def build_row_payload(record: dict[str, Any]) -> dict[str, Any]:
    now = backend_server.utc_now()
    payload = {column: "" for column in backend_server.SCHOOL_COLUMNS}
    payload.update(record)
    payload["created_at"] = record.get("created_at") or now
    payload["updated_at"] = record.get("updated_at") or now
    return payload


class BackendServerTestCase(unittest.TestCase):
    """Base de testes com servidor HTTP temporario e banco isolado."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.public_root = self.temp_path / "public"
        self.database_path = self.temp_path / "backend" / "data" / "schools.sqlite3"
        self._original_globals = {
            "PUBLIC_ROOT": backend_server.PUBLIC_ROOT,
            "STATIC_CONFIG_PATH": backend_server.STATIC_CONFIG_PATH,
            "DATABASE_PATH": backend_server.DATABASE_PATH,
        }

        self._build_temp_public_root()
        backend_server.PUBLIC_ROOT = self.public_root
        backend_server.STATIC_CONFIG_PATH = self.public_root / "data" / "config" / "app-config.json"
        backend_server.DATABASE_PATH = self.database_path

        self._seed_database(FIXTURE_ROWS)
        self.server = backend_server.ThreadingHTTPServer(("127.0.0.1", 0), backend_server.EscolasRequestHandler)
        self.port = self.server.server_address[1]
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self._wait_until_ready()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=5)
        backend_server.PUBLIC_ROOT = self._original_globals["PUBLIC_ROOT"]
        backend_server.STATIC_CONFIG_PATH = self._original_globals["STATIC_CONFIG_PATH"]
        backend_server.DATABASE_PATH = self._original_globals["DATABASE_PATH"]
        self.temp_dir.cleanup()

    def _build_temp_public_root(self) -> None:
        source_public = PROJECT_ROOT / "public"

        (self.public_root / "admin").mkdir(parents=True, exist_ok=True)
        (self.public_root / "assets" / "js").mkdir(parents=True, exist_ok=True)
        (self.public_root / "assets" / "css").mkdir(parents=True, exist_ok=True)
        (self.public_root / "data" / "config").mkdir(parents=True, exist_ok=True)
        (self.public_root / "data" / "schools").mkdir(parents=True, exist_ok=True)

        for relative_path in (
            Path("index.html"),
            Path("admin/index.html"),
            Path("assets/js/app.js"),
            Path("assets/js/admin.js"),
            Path("assets/css/styles.css"),
            Path("assets/css/admin.css"),
            Path("data/config/app-config.json"),
        ):
            target = self.public_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((source_public / relative_path).read_bytes())

    def _seed_database(self, rows: list[dict[str, Any]]) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = backend_server.get_connection()
        try:
            backend_server.create_schema(connection)
            connection.executemany(
                f"""
                INSERT INTO schools ({', '.join(backend_server.SCHOOL_COLUMNS)})
                VALUES ({', '.join('?' for _ in backend_server.SCHOOL_COLUMNS)})
                """,
                [
                    tuple(build_row_payload(row)[column] for column in backend_server.SCHOOL_COLUMNS)
                    for row in rows
                ],
            )
            backend_server.touch_data_version(connection)
            backend_server.write_static_exports(connection)
            connection.commit()
        finally:
            connection.close()

    def _wait_until_ready(self) -> None:
        deadline = time.time() + 5
        last_error = None
        while time.time() < deadline:
            try:
                status, _, _ = self.request("GET", "/api/health")
                if status == 200:
                    return
            except OSError as error:  # pragma: no cover - espera de boot
                last_error = error
                time.sleep(0.05)
        raise RuntimeError(f"Servidor de teste nao respondeu a tempo: {last_error}")

    def request(
        self,
        method: str,
        path: str,
        body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        request_headers = dict(headers or {})
        payload = None
        if body is not None:
            if isinstance(body, (dict, list)):
                payload = json.dumps(body).encode("utf-8")
                request_headers.setdefault("Content-Type", "application/json")
            elif isinstance(body, bytes):
                payload = body
            else:
                payload = str(body).encode("utf-8")
            request_headers.setdefault("Content-Length", str(len(payload)))

        connection.request(method, path, body=payload, headers=request_headers)
        response = connection.getresponse()
        response_body = response.read()
        response_headers = {key: value for key, value in response.getheaders()}
        connection.close()
        return response.status, response_headers, response_body

    def request_json(
        self,
        method: str,
        path: str,
        body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], Any]:
        status, response_headers, response_body = self.request(method, path, body=body, headers=headers)
        if response_body:
            parsed = json.loads(response_body.decode("utf-8"))
        else:
            parsed = None
        return status, response_headers, parsed

    def read_export_dataset(self, dataset_name: str) -> list[dict[str, Any]]:
        export_path = self.public_root / "data" / "schools" / dataset_name
        return json.loads(export_path.read_text(encoding="utf-8"))
