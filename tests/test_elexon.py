import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

from backend.elexon import fetch_actuals, fetch_forecasts
from backend.forecasts import select_forecasts


class ElexonTests(unittest.TestCase):
    @patch("backend.elexon.urlopen")
    def test_fetch_forecasts_connects_to_selection(self, open_url):
        records = [
            {"publishTime": "2026-01-10T07:30:00Z", "startTime": "2026-01-11T12:00:00Z", "generation": 19492},
            {"publishTime": "2026-01-10T09:30:00Z", "startTime": "2026-01-11T12:00:00Z", "generation": 19348},
        ]
        open_url.return_value = io.BytesIO(json.dumps(records).encode())
        cutoff = "2026-01-10T09:00:00Z"

        fetched = fetch_forecasts("2026-01-10T00:00:00Z", cutoff)

        self.assertEqual(select_forecasts(fetched, cutoff), [records[0]])
        url = urlparse(open_url.call_args.args[0].full_url)
        self.assertEqual(url.path, "/bmrs/api/v1/datasets/WINDFOR/stream")
        self.assertEqual(parse_qs(url.query), {
            "publishDateTimeFrom": ["2026-01-10T00:00:00Z"],
            "publishDateTimeTo": [cutoff],
        })

    @patch("backend.elexon.urlopen")
    def test_actuals_request_is_restricted_to_wind_and_delivery_date(self, open_url):
        open_url.return_value = io.BytesIO(b"[]")

        self.assertEqual(fetch_actuals("2026-01-11"), [])

        url = urlparse(open_url.call_args.args[0].full_url)
        self.assertEqual(url.path, "/bmrs/api/v1/datasets/FUELHH/stream")
        self.assertEqual(parse_qs(url.query), {
            "settlementDateFrom": ["2026-01-11"],
            "settlementDateTo": ["2026-01-11"],
            "fuelType": ["WIND"],
        })

    def test_network_failures_raise_instead_of_returning_missing_data(self):
        errors = [
            URLError("Network unavailable"),
            TimeoutError("Request timed out"),
            HTTPError("https://data.elexon.co.uk", 429, "Too many requests", None, None),
        ]
        for error in errors:
            with self.subTest(error=error), patch("backend.elexon.urlopen", side_effect=error):
                with self.assertRaisesRegex(RuntimeError, "Elexon FUELHH request failed") as caught:
                    fetch_actuals("2026-01-11")
                self.assertIs(caught.exception.__cause__, error)

    @patch("backend.elexon.urlopen")
    def test_invalid_json_raises_a_readable_error(self, open_url):
        open_url.return_value = io.BytesIO(b"<html>Service unavailable</html>")

        with self.assertRaisesRegex(RuntimeError, "Elexon FUELHH request failed"):
            fetch_actuals("2026-01-11")

    def test_unexpected_json_structure_is_rejected(self):
        for payload in ({"message": "Service unavailable"}, [123]):
            with self.subTest(payload=payload), patch("backend.elexon.urlopen") as open_url:
                open_url.return_value = io.BytesIO(json.dumps(payload).encode())
                with self.assertRaisesRegex(RuntimeError, "expected a list of records"):
                    fetch_actuals("2026-01-11")
