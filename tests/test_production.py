import re
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


@unittest.skipUnless(
    (Path(__file__).resolve().parents[1] / "frontend" / "dist" / "index.html").is_file(),
    "Run npm --prefix frontend run build before the production integration checks.",
)
class ProductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from backend.production import app

        cls.client = TestClient(app)

    def test_dashboard_and_generated_assets_are_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Winddesk", response.text)
        self.assertNotIn("/@vite/client", response.text)
        assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', response.text)
        self.assertTrue(assets)
        for asset in assets:
            with self.subTest(asset=asset):
                result = self.client.get(asset)
                self.assertEqual(result.status_code, 200)
                self.assertNotIn("text/html", result.headers["content-type"])

    @patch("backend.app.fetch_actuals", return_value=[])
    @patch("backend.app.fetch_forecasts", return_value=[])
    def test_api_remains_json_when_dashboard_is_enabled(self, forecasts, actuals):
        response = self.client.get("/api/day-ahead", params={"decision_date": "2026-01-10"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/json")
        self.assertEqual(response.json()["deliveryDate"], "2026-01-11")

    def test_missing_assets_api_routes_and_source_files_return_404(self):
        for path in ("/assets/missing.js", "/api/missing", "/backend/app.py", "/README.md"):
            with self.subTest(path=path):
                response = self.client.get(path, headers={"Accept": "text/html"})
                self.assertEqual(response.status_code, 404)
