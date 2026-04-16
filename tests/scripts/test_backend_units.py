from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from test_support import backend_server


class BackendHelpersTestCase(unittest.TestCase):
    def test_text_and_number_cleaners_cover_common_edge_cases(self) -> None:
        self.assertEqual(backend_server.clean_text(None), "")
        self.assertEqual(backend_server.clean_text("  null "), "")
        self.assertEqual(backend_server.clean_text(" Escola Sol "), "Escola Sol")

        self.assertIsNone(backend_server.clean_int(""))
        self.assertEqual(backend_server.clean_int("12,4"), 12)
        self.assertEqual(backend_server.clean_int("12.6"), 13)

        self.assertIsNone(backend_server.clean_float("undefined"))
        self.assertEqual(backend_server.clean_float("12,5"), 12.5)

    def test_build_export_address_avoids_duplicate_complement_and_district(self) -> None:
        address = backend_server.build_export_address(
            {
                "address": "Rua das Flores",
                "number": "10",
                "complement": "Bloco A",
                "district": "Centro",
            }
        )
        duplicated = backend_server.build_export_address(
            {
                "address": "Rua das Flores, 10, Centro",
                "number": "",
                "complement": "Centro",
                "district": "Centro",
            }
        )

        self.assertEqual(address, "Rua das Flores, 10, Bloco A, Centro")
        self.assertEqual(duplicated, "Rua das Flores, 10, Centro")

    def test_normalize_school_payload_applies_defaults_and_slugifies_detail_shard(self) -> None:
        payload = backend_server.normalize_school_payload(
            {
                "network_type": "municipais",
                "name": "Escola Aurora",
                "municipio": "Vila Velha",
                "latitude": "-20,35",
                "longitude": "-40.29",
                "teacher_count": "14,2",
                "student_count": "301",
            }
        )

        self.assertEqual(payload["network_type"], "municipais")
        self.assertEqual(payload["name_original"], "Escola Aurora")
        self.assertEqual(payload["uf"], "ES")
        self.assertEqual(payload["detail_shard"], "vila-velha")
        self.assertEqual(payload["teacher_count"], 14)
        self.assertEqual(payload["student_count"], 301)
        self.assertTrue(payload["id"].startswith("municipais_escola-aurora_"))

    def test_build_runtime_config_accepts_injected_dependencies(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            backend_server.create_schema(connection)
            backend_server.set_meta(connection, "data_version", "2026-04-16T00:00:00.000+00:00")
            config = backend_server.build_runtime_config(
                "http://127.0.0.1:8765",
                config_loader=lambda _path: {
                    "schoolLayers": [
                        {"id": "municipais", "dataPath": "data/schools/e_municipais.json"},
                        {"id": "federais", "dataPath": "data/schools/e_federais.json"},
                    ]
                },
                connection_factory=lambda: connection,
            )
        finally:
            connection.close()

        self.assertEqual(
            [item["dataPath"] for item in config["schoolLayers"]],
            ["/api/frontend/schools/municipais", "/api/frontend/schools/federais"],
        )
        self.assertEqual(config["runtime"]["apiBaseUrl"], "http://127.0.0.1:8765/api")
        self.assertEqual(config["runtime"]["dataVersion"], "2026-04-16T00:00:00.000+00:00")

    def test_build_import_rows_uses_injected_public_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            public_root = Path(temp_dir) / "public"
            schools_dir = public_root / "data" / "schools"
            schools_dir.mkdir(parents=True, exist_ok=True)
            (public_root / "data" / "config").mkdir(parents=True, exist_ok=True)

            (schools_dir / "e_municipais.json").write_text(
                '[{"Nome_escola":"Escola Sol","Municipio":"Vitoria","Endereco":"Rua A","Latitude":-20.31,"Longitude":-40.30}]',
                encoding="utf-8",
            )
            for dataset_name in ("e_estaduais.json", "e_federais.json", "e_privadas.json"):
                (schools_dir / dataset_name).write_text("[]", encoding="utf-8")

            rows = backend_server.build_import_rows(public_root=public_root)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["network_type"], "municipais")
        self.assertEqual(rows[0]["georef_source"], backend_server.SNAPSHOT_IMPORT_SOURCE)
        self.assertEqual(rows[0]["detail_shard"], "vitoria")

    def test_parse_limit_and_offset_enforce_bounds(self) -> None:
        self.assertEqual(backend_server.parse_limit("abc"), 50)
        self.assertEqual(backend_server.parse_limit("0"), 1)
        self.assertEqual(backend_server.parse_limit("999"), 500)
        self.assertEqual(backend_server.parse_offset("-5"), 0)
        self.assertEqual(backend_server.parse_offset("12"), 12)


if __name__ == "__main__":
    unittest.main()
