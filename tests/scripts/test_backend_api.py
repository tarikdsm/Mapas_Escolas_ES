from __future__ import annotations

import time
import urllib.parse
from unittest.mock import patch

from test_support import BackendServerTestCase, FIXTURE_ROWS, backend_server, build_row_payload


class BackendApiTestCase(BackendServerTestCase):
    def test_initial_import_uses_current_frontend_exports(self) -> None:
        rows = backend_server.build_import_rows()

        self.assertEqual(len(rows), len(FIXTURE_ROWS))
        self.assertEqual({row["network_type"] for row in rows}, {"municipais", "estaduais", "federais"})
        self.assertTrue(all(row["georef_source"] == backend_server.SNAPSHOT_IMPORT_SOURCE for row in rows))
        self.assertTrue(all(row["id"] for row in rows))
        self.assertTrue(any(row["name"] == "Escola Sol" for row in rows))

    def test_health_and_runtime_config_are_available(self) -> None:
        status, headers, payload = self.request_json("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(headers["Access-Control-Allow-Origin"], "*")

        status, _, meta = self.request_json("GET", "/api/meta")
        self.assertEqual(status, 200)
        self.assertEqual(meta["sourceOfTruth"], "sqlite")
        self.assertTrue(meta["snapshotExportsEnabled"])

        status, _, config = self.request_json("GET", "/api/config")
        self.assertEqual(status, 200)
        self.assertTrue(config["runtime"]["apiEnabled"])
        self.assertEqual(config["runtime"]["adminUrl"], "/admin/")
        self.assertTrue(
            all(layer["dataPath"].startswith("/api/frontend/schools/") for layer in config["schoolLayers"])
        )

    def test_ensure_database_ready_recreates_database_from_current_exports(self) -> None:
        original_exports = {
            "e_municipais.json": self.read_export_dataset("e_municipais.json"),
            "e_estaduais.json": self.read_export_dataset("e_estaduais.json"),
            "e_federais.json": self.read_export_dataset("e_federais.json"),
            "e_privadas.json": self.read_export_dataset("e_privadas.json"),
        }

        self.assertTrue(self.database_path.exists())
        self.database_path.unlink()
        self.assertFalse(self.database_path.exists())

        backend_server.ensure_database_ready()

        self.assertTrue(self.database_path.exists())

        status, _, meta = self.request_json("GET", "/api/meta")
        self.assertEqual(status, 200)
        self.assertGreater(meta["schoolCount"], 0)
        self.assertEqual(meta["schoolCount"], len(FIXTURE_ROWS))

        rebuilt_rows = backend_server.build_import_rows()
        self.assertEqual(len(rebuilt_rows), len(FIXTURE_ROWS))

        for dataset_name, original_rows in original_exports.items():
            self.assertEqual(self.read_export_dataset(dataset_name), original_rows)

    def test_meta_endpoint_supports_etag_and_304_until_data_version_changes(self) -> None:
        status, headers, payload = self.request_json("GET", "/api/meta")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("ETag", headers)

        first_etag = headers["ETag"]
        self.assertEqual(first_etag, '"' + payload["dataVersion"] + '"')

        status, headers, payload = self.request_json(
            "GET",
            "/api/meta",
            headers={"If-None-Match": first_etag},
        )
        self.assertEqual(status, 304)
        self.assertEqual(payload, None)
        self.assertEqual(headers["ETag"], first_etag)

        status, _, created = self.request_json(
            "POST",
            "/api/schools",
            body={
                "network_type": "municipais",
                "name": "Escola Etag",
                "municipio": "Cariacica",
                "latitude": -20.2642,
                "longitude": -40.4208,
            },
        )
        self.assertEqual(status, 201)

        status, headers, payload = self.request_json(
            "GET",
            "/api/meta",
            headers={"If-None-Match": first_etag},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(headers["ETag"], '"' + payload["dataVersion"] + '"')
        self.assertNotEqual(headers["ETag"], first_etag)
        self.assertEqual(payload["schoolCount"], len(FIXTURE_ROWS) + 1)

    def test_filters_accept_municipio_with_or_without_accent(self) -> None:
        status, _, payload = self.request_json(
            "GET",
            "/api/schools?municipio=" + urllib.parse.quote("Vitória") + "&limit=10",
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["total"], 2)

        status, _, payload = self.request_json(
            "GET",
            "/api/schools?municipio=" + urllib.parse.quote("Vitoria") + "&limit=10",
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["total"], 2)

    def test_post_rejects_external_origin_on_write_routes(self) -> None:
        initial_count = self.count_schools()
        status, headers, payload = self.request_json(
            "POST",
            "/api/schools",
            body={
                "network_type": "municipais",
                "name": "Escola Origem Externa",
                "municipio": "Cariacica",
                "latitude": -20.2642,
                "longitude": -40.4208,
            },
            headers={"Origin": "https://evil.example"},
        )

        self.assertEqual(status, 403)
        self.assertEqual(payload["error"], "Origem nao autorizada para operacoes de escrita.")
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertEqual(self.count_schools(), initial_count)

    def test_create_school_persists_in_temp_database_and_frontend_export(self) -> None:
        new_school = {
            "network_type": "municipais",
            "name": "Escola Aurora",
            "municipio": "Cariacica",
            "uf": "ES",
            "status": "Em Atividade",
            "address": "Rua da Aurora",
            "number": "55",
            "postal_code": "29140-000",
            "teacher_count": 9,
            "student_count": 210,
            "latitude": -20.2642,
            "longitude": -40.4208,
        }
        initial_count = self.count_schools()

        status, _, created = self.request_json("POST", "/api/schools", body=new_school)
        self.assertEqual(status, 201)
        self.assertEqual(created["name"], "Escola Aurora")
        self.assertEqual(created["network_type"], "municipais")
        self.assertEqual(self.count_schools(), initial_count + 1)

        saved_row = self.fetch_school_row(created["id"])
        self.assertIsNotNone(saved_row)
        self.assertEqual(saved_row["name"], "Escola Aurora")
        self.assertEqual(saved_row["municipio"], "Cariacica")
        self.assertEqual(saved_row["teacher_count"], 9)
        self.assertEqual(saved_row["student_count"], 210)

        status, _, dataset = self.request_json("GET", "/api/frontend/schools/municipais")
        self.assertEqual(status, 200)
        dataset_row = next(item for item in dataset if item["Nome_escola"] == "Escola Aurora")
        self.assertEqual(dataset_row["Municipio"], "Cariacica")
        self.assertEqual(dataset_row["Numero_professores"], 9)
        self.assertEqual(dataset_row["Numero_alunos"], 210)

        self.flush_exports()
        export_rows = self.read_export_dataset("e_municipais.json")
        export_row = next(item for item in export_rows if item["Nome_escola"] == "Escola Aurora")
        self.assertEqual(export_row["Municipio"], "Cariacica")
        self.assertEqual(export_row["Numero_professores"], 9)
        self.assertEqual(export_row["Numero_alunos"], 210)

    def test_update_school_persists_changes_in_temp_database_and_frontend_export(self) -> None:
        school_id = FIXTURE_ROWS[0]["id"]
        before_row = self.fetch_school_row(school_id)

        self.assertIsNotNone(before_row)
        self.assertEqual(before_row["name"], "Escola Sol")

        status, _, updated = self.request_json(
            "PUT",
            "/api/schools/" + urllib.parse.quote(school_id),
            body={
                "network_type": "municipais",
                "name": "Escola Sol Atualizada",
                "municipio": "Cariacica",
                "uf": "ES",
                "address": "Rua do Sol",
                "number": "101",
                "teacher_count": 10,
                "student_count": 215,
                "latitude": -20.2642,
                "longitude": -40.4208,
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["id"], school_id)
        self.assertEqual(updated["name"], "Escola Sol Atualizada")
        self.assertEqual(updated["teacher_count"], 10)

        saved_row = self.fetch_school_row(school_id)
        self.assertIsNotNone(saved_row)
        self.assertEqual(saved_row["name"], "Escola Sol Atualizada")
        self.assertEqual(saved_row["municipio"], "Cariacica")
        self.assertEqual(saved_row["number"], "101")
        self.assertEqual(saved_row["teacher_count"], 10)
        self.assertEqual(saved_row["student_count"], 215)

        self.flush_exports()
        export_rows = self.read_export_dataset("e_municipais.json")
        export_row = next(item for item in export_rows if item["Nome_escola"] == "Escola Sol Atualizada")
        self.assertEqual(export_row["Municipio"], "Cariacica")
        self.assertEqual(export_row["Numero_professores"], 10)
        self.assertEqual(export_row["Numero_alunos"], 215)

    def test_delete_school_removes_from_temp_database_and_frontend_export(self) -> None:
        school_id = FIXTURE_ROWS[0]["id"]
        initial_count = self.count_schools()

        self.assertIsNotNone(self.fetch_school_row(school_id))

        status, _, deleted = self.request_json("DELETE", "/api/schools/" + urllib.parse.quote(school_id))
        self.assertEqual(status, 200)
        self.assertTrue(deleted["deleted"])
        self.assertEqual(deleted["id"], school_id)
        self.assertEqual(self.count_schools(), initial_count - 1)
        self.assertIsNone(self.fetch_school_row(school_id))

        self.flush_exports()
        export_rows = self.read_export_dataset("e_municipais.json")
        self.assertFalse(any(item["Nome_escola"] == "Escola Sol" for item in export_rows))
        self.assertFalse(any(item["Nome_escola"] == "Escola Sol Atualizada" for item in export_rows))

    def test_batched_posts_trigger_single_export_flush_and_match_database(self) -> None:
        original_write_static_exports = backend_server.write_static_exports
        export_write_count = 0

        def counting_write_static_exports(connection):
            nonlocal export_write_count
            export_write_count += 1
            return original_write_static_exports(connection)

        backend_server.write_static_exports = counting_write_static_exports
        try:
            for index in range(20):
                payload = {
                    "network_type": "municipais",
                    "name": f"Escola Lote {index}",
                    "municipio": "Cariacica",
                    "uf": "ES",
                    "address": f"Rua Lote {index}",
                    "number": str(index + 1),
                    "teacher_count": index + 1,
                    "student_count": 100 + index,
                    "latitude": -20.2642,
                    "longitude": -40.4208,
                }
                status, _, created = self.request_json("POST", "/api/schools", body=payload)
                self.assertEqual(status, 201)
                self.assertEqual(created["name"], f"Escola Lote {index}")

            time.sleep(0.2)
            self.assertEqual(export_write_count, 0)

            self.flush_exports()
            self.assertEqual(export_write_count, 1)
        finally:
            backend_server.write_static_exports = original_write_static_exports

        connection = backend_server.get_connection()
        try:
            municipal_count = connection.execute(
                "SELECT COUNT(*) AS total FROM schools WHERE network_type = ?",
                ("municipais",),
            ).fetchone()["total"]
        finally:
            connection.close()

        export_rows = self.read_export_dataset("e_municipais.json")
        export_names = {item["Nome_escola"] for item in export_rows}

        self.assertEqual(len(export_rows), int(municipal_count))
        for index in range(20):
            self.assertIn(f"Escola Lote {index}", export_names)

    def test_update_missing_school_returns_not_found_without_creating_row(self) -> None:
        status, _, payload = self.request_json(
            "PUT",
            "/api/schools/municipais_inexistente_123",
            body={
                "network_type": "municipais",
                "name": "Escola Fantasma",
                "municipio": "Cariacica",
                "latitude": -20.2642,
                "longitude": -40.4208,
            },
        )

        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "Escola nao encontrada.")

        status, _, listing = self.request_json("GET", "/api/schools?q=Escola%20Fantasma&limit=10")
        self.assertEqual(status, 200)
        self.assertEqual(listing["total"], 0)

    def test_static_path_traversal_is_blocked(self) -> None:
        status, _, body = self.request("GET", "/../README.md")
        self.assertEqual(status, 404)
        self.assertNotIn(b"Mapas das Escolas", body)

    def test_internal_errors_do_not_leak_exception_details(self) -> None:
        original = backend_server.build_meta_response
        original_traceback = backend_server.traceback.print_exc
        had_module_print = hasattr(backend_server, "print")
        original_print = getattr(backend_server, "print", None)

        def boom() -> dict[str, str]:
            raise RuntimeError("senha-super-secreta")

        backend_server.build_meta_response = boom
        backend_server.traceback.print_exc = lambda: None
        backend_server.print = lambda *args, **kwargs: None
        try:
            status, _, payload = self.request_json("GET", "/api/meta")
        finally:
            backend_server.build_meta_response = original
            backend_server.traceback.print_exc = original_traceback
            if had_module_print:
                backend_server.print = original_print
            else:
                delattr(backend_server, "print")

        self.assertEqual(status, 500)
        self.assertEqual(payload["error"], "Falha interna no servidor.")
        self.assertNotIn("senha-super-secreta", str(payload))

    def test_large_request_body_is_rejected(self) -> None:
        oversized_notes = "x" * (backend_server.MAX_REQUEST_BODY_BYTES + 32)
        payload = {
            "network_type": "municipais",
            "name": "Escola Corpo Grande",
            "municipio": "Vitória",
            "latitude": -20.31,
            "longitude": -40.31,
            "notes": oversized_notes,
        }
        status, _, response = self.request_json("POST", "/api/schools", body=payload)
        self.assertEqual(status, 400)
        self.assertIn("excede o limite", response["error"])

    def test_school_list_endpoint_stays_fast_with_more_rows(self) -> None:
        connection = backend_server.get_connection()
        try:
            bulk_rows = []
            for index in range(500):
                row = build_row_payload(
                    {
                        **FIXTURE_ROWS[0],
                        "id": f"municipais_bulk_{index}",
                        "name": f"Escola Bulk {index}",
                        "name_original": f"Escola Bulk {index}",
                        "inep_code": f"900{index}",
                    }
                )
                bulk_rows.append(tuple(row[column] for column in backend_server.SCHOOL_COLUMNS))
            connection.executemany(
                f"""
                INSERT INTO schools ({', '.join(backend_server.SCHOOL_COLUMNS)})
                VALUES ({', '.join('?' for _ in backend_server.SCHOOL_COLUMNS)})
                """,
                bulk_rows,
            )
            backend_server.touch_data_version(connection)
            connection.commit()
        finally:
            connection.close()

        start = time.perf_counter()
        status, _, payload = self.request_json("GET", "/api/schools?limit=50")
        elapsed = time.perf_counter() - start

        self.assertEqual(status, 200)
        self.assertEqual(len(payload["items"]), 50)
        self.assertLess(elapsed, 1.0)

    def test_main_blocks_remote_bind_without_explicit_opt_in(self) -> None:
        with patch.dict("os.environ", {"ESCOLAS_HOST": "0.0.0.0"}, clear=False):
            with patch.dict("os.environ", {"ESCOLAS_ALLOW_REMOTE": ""}, clear=False):
                with self.assertRaises(SystemExit) as context:
                    backend_server.main()

        self.assertIn("ESCOLAS_ALLOW_REMOTE=1", str(context.exception))
