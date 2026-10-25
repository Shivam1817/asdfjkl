import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.forecast = {
            "publishTime": "2026-01-10T07:30:00Z",
            "startTime": "2026-01-11T12:00:00Z",
            "generation": 19492,
        }
        self.actual = {
            "publishTime": "2026-01-11T12:30:00Z",
            "startTime": "2026-01-11T12:00:00Z",
            "generation": 15401,
        }

    @patch("backend.app.fetch_actuals")
    @patch("backend.app.fetch_forecasts")
    def test_daily_pipeline_excludes_late_forecasts_and_other_delivery_days(self, forecasts, actuals):
        forecasts.return_value = [
            self.forecast,
            dict(self.forecast, publishTime="2026-01-10T09:30:00Z", generation=19348),
            dict(self.forecast, startTime="2026-01-10T12:00:00Z"),
            dict(self.forecast, startTime="2026-01-12T12:00:00Z"),
            dict(self.forecast, startTime="2026-01-11T00:30:00+01:00"),
        ]
        actuals.return_value = [self.actual]

        response = self.client.get("/api/day-ahead", params={"decision_date": "2026-01-10"})

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["deliveryDate"], "2026-01-11")
        self.assertEqual(result["decisionTime"], "2026-01-10T09:00:00+00:00")
        self.assertEqual(result["expectedForecastCount"], 24)
        self.assertEqual(result["comparison"][0]["errorMW"], 4091)
        self.assertEqual(result["metrics"]["forecastCount"], 1)
        self.assertEqual(result["metrics"]["matchedCount"], 1)
        forecasts.assert_called_once_with("2026-01-08T09:00:00+00:00", "2026-01-10T09:00:00+00:00")
        actuals.assert_called_once_with("2026-01-11")

    @patch("backend.app.fetch_actuals", return_value=[])
    @patch("backend.app.fetch_forecasts", return_value=[])
    def test_january_boundaries_and_custom_decision_time(self, forecasts, actuals):
        for decision, delivery in (("2026-01-01", "2026-01-02"), ("2026-01-31", "2026-02-01")):
            with self.subTest(decision=decision):
                response = self.client.get("/api/day-ahead", params={
                    "decision_date": decision, "decision_time": "08:45",
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["decisionTime"], f"{decision}T08:45:00+00:00")
                self.assertEqual(response.json()["deliveryDate"], delivery)
                actuals.assert_called_with(delivery)

    @patch("backend.app.fetch_actuals")
    @patch("backend.app.fetch_forecasts")
    def test_invalid_queries_are_rejected_before_fetching(self, forecasts, actuals):
        queries = [{}, {"decision_date": "2025-12-31"}, {"decision_date": "2026-02-01"},
                   {"decision_date": "2026-01-99"}]
        queries += [{"decision_date": "2026-01-10", "decision_time": value}
                    for value in ("24:00", "09:60", "9:00", "09:00Z")]
        for query in queries:
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/api/day-ahead", params=query).status_code, 422)
        forecasts.assert_not_called()
        actuals.assert_not_called()

    @patch("backend.app.fetch_forecasts", side_effect=RuntimeError("Elexon unavailable"))
    def test_upstream_failure_returns_502(self, forecasts):
        with self.assertLogs("backend.app", level="ERROR"):
            response = self.client.get("/api/day-ahead", params={"decision_date": "2026-01-10"})
        self.assertEqual(response.status_code, 502)
        self.assertIn("Elexon", response.json()["detail"])

    @patch("backend.app.fetch_actuals")
    @patch("backend.app.fetch_forecasts")
    def test_invalid_upstream_records_return_502(self, forecasts, actuals):
        actuals.return_value = [self.actual]
        for record in ({}, dict(self.forecast, startTime="invalid"),
                       dict(self.forecast, generation="invalid")):
            with self.subTest(record=record), self.assertLogs("backend.app", level="ERROR"):
                forecasts.return_value = [record]
                response = self.client.get("/api/day-ahead", params={"decision_date": "2026-01-10"})
                self.assertEqual(response.status_code, 502)

    @patch("backend.app.fetch_actuals", return_value=[])
    @patch("backend.app.fetch_forecasts", return_value=[])
    def test_empty_data_returns_success_with_null_metrics(self, forecasts, actuals):
        response = self.client.get("/api/day-ahead", params={"decision_date": "2026-01-10"})

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["comparison"], [])
        self.assertEqual(result["metrics"]["matchedCount"], 0)
        self.assertIsNone(result["metrics"]["maeMW"])
        self.assertIsNone(result["metrics"]["rmseMW"])
        self.assertIsNone(result["metrics"]["biasMW"])
