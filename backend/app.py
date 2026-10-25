"""HTTP access to the wind forecast analysis pipeline."""

import logging
from datetime import date, datetime, time, timedelta, timezone

from fastapi import FastAPI, HTTPException, Query

from backend.analysis import calculate_metrics, compare_forecasts
from backend.elexon import fetch_actuals, fetch_forecasts
from backend.forecasts import parse_time, select_forecasts

app = FastAPI(title="Wind Forecast API")
logger = logging.getLogger(__name__)


@app.get("/api/day-ahead")
def day_ahead(
    decision_date: date = Query(..., ge=date(2026, 1, 1), le=date(2026, 1, 31)),
    decision_time: str = Query("09:00", pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$"),
) -> dict:
    """Analyze delivery on the next calendar day after a January 2026 decision.

    Decision times are UK time (UTC in January). The default 09:00 is a demo
    assumption. Search the preceding 48 hours of forecast publications.
    Accuracy uses matching start times: hourly forecasts versus half-hourly outturn.
    """
    cutoff = datetime.combine(decision_date, time.fromisoformat(decision_time), timezone.utc)
    delivery_start = datetime.combine(decision_date + timedelta(days=1), time(), timezone.utc)
    delivery_end = delivery_start + timedelta(days=1)
    published_from = (cutoff - timedelta(days=2)).isoformat()

    try:
        records = fetch_forecasts(published_from, cutoff.isoformat())
        selected = [
            row for row in select_forecasts(records, cutoff.isoformat())
            if delivery_start <= parse_time(row["startTime"]) < delivery_end
        ]
        actuals = fetch_actuals(delivery_start.date().isoformat())
        comparison = compare_forecasts(selected, actuals)
        metrics = calculate_metrics(comparison)
    except (RuntimeError, ValueError, KeyError, TypeError) as error:
        logger.exception("Could not analyze Elexon wind data")
        raise HTTPException(
            status_code=502,
            detail="Unable to load valid Elexon wind data. Please try again.",
        ) from error

    return {
        "decisionTime": cutoff.isoformat(),
        "deliveryDate": delivery_start.date().isoformat(),
        "timezone": "Europe/London",
        "expectedForecastCount": 24,
        "comparison": comparison,
        "metrics": metrics,
    }
