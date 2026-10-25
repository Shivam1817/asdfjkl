import unittest

from backend.forecasts import select_forecasts


def record(published, delivery="2026-01-11T12:00:00Z", generation=19492):
    return {"publishTime": published, "startTime": delivery, "generation": generation}


class SelectForecastsTests(unittest.TestCase):
    def test_latest_available_per_delivery_and_chronological_output(self):
        noon = record("2026-01-10T07:30:00Z")
        morning = record("2026-01-10T07:30:00Z", "2026-01-11T08:00:00Z")
        older = record("2026-01-10T04:30:00Z", generation=19688)
        too_late = record("2026-01-10T09:30:00Z", generation=19348)
        forecasts = [too_late, noon, morning, older]
        original = [row.copy() for row in forecasts]

        result = select_forecasts(forecasts, "2026-01-10T09:00:00Z")

        self.assertEqual(result, [morning, noon])
        self.assertEqual(forecasts, original)

    def test_cutoff_is_inclusive_and_equivalent_offsets_match(self):
        older = record("2026-01-10T08:00:00Z")
        at_cutoff = record("2026-01-10T10:00:00+01:00", "2026-01-11T13:00:00+01:00")

        result = select_forecasts([older, at_cutoff], "2026-01-10T09:00:00Z")

        self.assertEqual(result, [at_cutoff])

    def test_missing_forecasts_remain_missing(self):
        for forecasts in ([], [record("2026-01-10T09:30:00Z")]):
            with self.subTest(forecasts=forecasts):
                self.assertEqual(select_forecasts(forecasts, "2026-01-10T09:00:00Z"), [])

    def test_equal_publications_keep_first_record(self):
        first = record("2026-01-10T07:30:00Z")
        duplicate = record("2026-01-10T07:30:00Z", generation=19000)

        self.assertEqual(select_forecasts([first, duplicate], "2026-01-10T09:00:00Z"), [first])

    def test_timestamps_without_timezone_are_rejected(self):
        for field in ("decision_time", "publishTime", "startTime"):
            with self.subTest(field=field):
                forecast = record("2026-01-10T07:30:00Z")
                cutoff = "2026-01-10T09:00:00Z"
                if field == "decision_time":
                    cutoff = cutoff.removesuffix("Z")
                else:
                    forecast[field] = forecast[field].removesuffix("Z")
                with self.assertRaisesRegex(ValueError, "timezone"):
                    select_forecasts([forecast], cutoff)
