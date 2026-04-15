from __future__ import annotations

import time
import urllib.parse

from test_support import BackendServerTestCase, FIXTURE_ROWS, backend_server, build_row_payload


class BackendApiTestCase(BackendServerTestCase):
    def test_initial_import_uses_current_frontend_exports(self) -> None:
        rows = backend_server.build_import_rows()

        self.assertEqual(len(rows), len(FIXTURE_ROWS))
        self.assertEqual({row["network_type"] for row in rows}, {"municipais", "estaduais", "federais"})
        self.assertTrue(all(row["georef_source"] == "frontend-static-export" for row in rows))
        self.assertTrue(all(row["id"] for row in rows))
        self.assertTrue(any(row["name"] == "Escola Sol" for row in rows))

    def test_health_and_runtime_config_are_available(self) -> None:
        status, headers, payload = self.request_json("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(headers["Access-Control-Allow-Origin"], "*")

        status, _, config = self.request_json("GET", "/api/config")
        self.assertEqual(status, 200)
        self.assertTrue(config["runtime"]["apiEnabled"])
        self.assertEqual(config["runtime"]["adminUrl"], "/admin/")
        self.assertTrue(
            all(layer["dataPath"].startswith("/api/frontend/schools/") for layer in config["schoolLayers"])
        )

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

    def test_create_update_delete_school_refreshes_frontend_exports(self) -> None:
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

        status, _, created = self.request_json("POST", "/api/schools", body=new_school)
        self.assertEqual(status, 201)
        self.assertEqual(created["name"], "Escola Aurora")
        self.assertEqual(created["network_type"], "municipais")

        status, _, dataset = self.request_json("GET", "/api/frontend/schools/municipais")
        self.assertEqual(status, 200)
        self.assertTrue(any(item["Nome_escola"] == "Escola Aurora" for item in dataset))

        export_rows = self.read_export_dataset("e_municipais.json")
        self.assertTrue(any(item["Nome_escola"] == "Escola Aurora" for item in export_rows))

        status, _, updated = self.request_json(
            "PUT",
            "/api/schools/" + urllib.parse.quote(created["id"]),
            body={
                "network_type": "municipais",
                "name": "Escola Aurora Atualizada",
                "municipio": "Cariacica",
                "uf": "ES",
                "address": "Rua da Aurora",
                "number": "55",
                "teacher_count": 10,
                "student_count": 215,
                "latitude": -20.2642,
                "longitude": -40.4208,
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["name"], "Escola Aurora Atualizada")
        self.assertEqual(updated["teacher_count"], 10)

        export_rows = self.read_export_dataset("e_municipais.json")
        self.assertTrue(any(item["Nome_escola"] == "Escola Aurora Atualizada" for item in export_rows))

        status, _, deleted = self.request_json(
            "DELETE",
            "/api/schools/" + urllib.parse.quote(created["id"]),
        )
        self.assertEqual(status, 200)
        self.assertTrue(deleted["deleted"])

        export_rows = self.read_export_dataset("e_municipais.json")
        self.assertFalse(any(item["Nome_escola"] == "Escola Aurora Atualizada" for item in export_rows))

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
