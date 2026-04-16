from __future__ import annotations

from test_support import BackendServerTestCase


class StaticPagesTestCase(BackendServerTestCase):
    def test_map_page_contains_backend_link(self) -> None:
        status, headers, body = self.request("GET", "/")
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("Abrir backend", html)
        self.assertIn("data-admin-link", html)

    def test_admin_page_contains_map_link(self) -> None:
        status, headers, body = self.request("GET", "/admin/")
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("Abrir mapa", html)
        self.assertIn("school-table-body", html)
        self.assertIn("Rede administrativa", html)
        self.assertIn("Nome da escola", html)
        self.assertIn("Nova escola", html)

    def test_static_assets_are_served(self) -> None:
        status, headers, body = self.request("GET", "/assets/js/app.js")
        self.assertEqual(status, 200)
        self.assertIn("javascript", headers["Content-Type"])
        self.assertIn(b"loadConfig", body)

    def test_admin_notes_popover_assets_include_viewport_positioning(self) -> None:
        status, headers, body = self.request("GET", "/assets/js/admin.js")
        js = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("javascript", headers["Content-Type"])
        self.assertIn("function positionOpenNotesPopover()", js)
        self.assertIn('popover.setAttribute("data-placement", openAbove ? "top" : "bottom")', js)

        status, headers, body = self.request("GET", "/assets/css/admin.css")
        css = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/css", headers["Content-Type"])
        self.assertIn(".sheet-note-popover {", css)
        self.assertIn("position: fixed;", css)
        self.assertIn("max-height: calc(100vh - 24px);", css)

    def test_published_admin_bundle_does_not_hardcode_local_backend_urls(self) -> None:
        status, headers, body = self.request("GET", "/assets/js/admin.js")
        js = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("javascript", headers["Content-Type"])
        self.assertNotIn("http://127.0.0.1", js)
        self.assertNotIn("localhost", js)
        self.assertNotIn(":8765", js)
