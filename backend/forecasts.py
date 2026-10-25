"""Select the wind forecasts available at a historical decision time."""

from datetime import datetime


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("Timestamps must include a timezone, such as Z or +00:00")
    return parsed


def select_forecasts(forecasts: list[dict], decision_time: str) -> list[dict]:
    """Return the latest forecast per delivery time, ordered by delivery time.

    Publications exactly at the decision time are eligible. Equal publication
    times keep the first record supplied. Input records are left unchanged.
    """
    cutoff = parse_time(decision_time)
    selected = {}

    for forecast in forecasts:
        published = parse_time(forecast["publishTime"])
        if published > cutoff:
            continue

        delivery = parse_time(forecast["startTime"])
        previous = selected.get(delivery)
        if previous is None or published > parse_time(previous["publishTime"]):
            selected[delivery] = forecast

    return [selected[delivery] for delivery in sorted(selected)]
