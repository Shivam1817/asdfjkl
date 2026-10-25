"""Fetch the two Elexon datasets used by the application."""

import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"


def _fetch(dataset: str, parameters: dict) -> list[dict]:
    url = f"{BASE_URL}/{dataset}/stream?{urlencode(parameters)}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            records = json.load(response)
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Elexon {dataset} request failed: {error}") from error

    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise RuntimeError(f"Elexon {dataset} returned an unexpected response; expected a list of records")
    return records


def fetch_forecasts(published_from: str, published_to: str) -> list[dict]:
    """Fetch WINDFOR by publication time; supply timezone-aware ISO timestamps."""
    return _fetch("WINDFOR", {
        "publishDateTimeFrom": published_from,
        "publishDateTimeTo": published_to,
    })


def fetch_actuals(delivery_date: str) -> list[dict]:
    """Fetch WIND outturn for one settlement date, supplied as YYYY-MM-DD."""
    return _fetch("FUELHH", {
        "settlementDateFrom": delivery_date,
        "settlementDateTo": delivery_date,
        "fuelType": "WIND",
    })
