"""Compare selected forecasts with outturn at matching delivery timestamps."""

from math import isfinite, sqrt

from backend.forecasts import parse_time


def compare_forecasts(forecasts: list[dict], actuals: list[dict]) -> list[dict]:
    """Keep each selected forecast; use the latest actual revision when available.

    Matching uses identical start times, without interpolation or averaging.
    Error is forecast minus actual, so a positive error means overforecasting.
    """
    actual_by_time = {}
    for actual in actuals:
        delivery = parse_time(actual["startTime"])
        previous = actual_by_time.get(delivery)
        if previous is None or parse_time(actual["publishTime"]) > parse_time(previous["publishTime"]):
            actual_by_time[delivery] = actual

    comparison = []
    for forecast in forecasts:
        actual = actual_by_time.get(parse_time(forecast["startTime"]))
        forecast_mw = forecast["generation"]
        actual_mw = actual["generation"] if actual is not None else None
        if any(value is not None and not isfinite(value) for value in (forecast_mw, actual_mw)):
            raise ValueError("Generation values must be finite numbers or None")
        error = forecast_mw - actual_mw if forecast_mw is not None and actual_mw is not None else None
        comparison.append({
            "startTime": forecast["startTime"],
            "publishTime": forecast["publishTime"],
            "forecastMW": forecast_mw,
            "actualMW": actual_mw,
            "errorMW": error,
        })
    return comparison


def calculate_metrics(comparison: list[dict]) -> dict:
    """Summarize valid matches in MW; return None for metrics with no matches."""
    errors = [row["errorMW"] for row in comparison if row["errorMW"] is not None]
    count = len(errors)
    return {
        "forecastCount": len(comparison),
        "matchedCount": count,
        "maeMW": sum(abs(error) for error in errors) / count if count else None,
        "rmseMW": sqrt(sum(error ** 2 for error in errors) / count) if count else None,
        "biasMW": sum(errors) / count if count else None,
    }
