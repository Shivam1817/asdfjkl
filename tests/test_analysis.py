import unittest

from backend.analysis import calculate_metrics, compare_forecasts


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.forecast = {
            "startTime": "2026-01-11T12:00:00Z",
            "publishTime": "2026-01-10T07:30:00Z",
            "generation": 19492,
        }
        self.actual = {
            "startTime": "2026-01-11T12:00:00Z",
            "publishTime": "2026-01-11T12:30:00Z",
            "generation": 15401,
        }

    def test_matches_equivalent_timestamps_and_retains_forecast_publication(self):
        self.actual["startTime"] = "2026-01-11T13:00:00+01:00"

        comparison = compare_forecasts([self.forecast], [self.actual])

        self.assertEqual(comparison, [{
            "startTime": "2026-01-11T12:00:00Z",
            "publishTime": "2026-01-10T07:30:00Z",
            "forecastMW": 19492,
            "actualMW": 15401,
            "errorMW": 4091,
        }])

    def test_latest_actual_revision_is_used_regardless_of_input_order(self):
        revision = dict(self.actual, publishTime="2026-01-11T13:00:00Z", generation=15000)
        for actuals in ([self.actual, revision], [revision, self.actual]):
            with self.subTest(actuals=actuals):
                comparison = compare_forecasts([self.forecast], actuals)
                self.assertEqual(comparison[0]["actualMW"], 15000)

    def test_another_half_hour_does_not_fill_a_missing_actual(self):
        self.actual["startTime"] = "2026-01-11T12:30:00Z"

        comparison = compare_forecasts([self.forecast], [self.actual])

        self.assertEqual(len(comparison), 1)
        self.assertEqual(comparison[0]["forecastMW"], 19492)
        self.assertIsNone(comparison[0]["actualMW"])
        self.assertIsNone(comparison[0]["errorMW"])

    def test_null_values_are_excluded_but_zero_is_a_valid_match(self):
        for forecast_mw, actual_mw, expected_count in ((None, 0, 0), (0, None, 0), (0, 0, 1)):
            with self.subTest(forecast=forecast_mw, actual=actual_mw):
                self.forecast["generation"] = forecast_mw
                self.actual["generation"] = actual_mw
                comparison = compare_forecasts([self.forecast], [self.actual])
                metrics = calculate_metrics(comparison)
                self.assertEqual(metrics["matchedCount"], expected_count)
                self.assertEqual(metrics["maeMW"], 0 if expected_count else None)

    def test_metrics_distinguish_error_magnitude_from_direction(self):
        comparison = [{"errorMW": value} for value in (100, -300, 0, None)]

        metrics = calculate_metrics(comparison)

        self.assertEqual(metrics["forecastCount"], 4)
        self.assertEqual(metrics["matchedCount"], 3)
        self.assertAlmostEqual(metrics["maeMW"], 133.33333333333334)
        self.assertAlmostEqual(metrics["rmseMW"], 182.57418583505537)
        self.assertAlmostEqual(metrics["biasMW"], -66.66666666666667)

    def test_no_matches_returns_null_metrics(self):
        for comparison in ([], [{"errorMW": None}]):
            with self.subTest(comparison=comparison):
                metrics = calculate_metrics(comparison)
                self.assertEqual(metrics["matchedCount"], 0)
                for name in ("maeMW", "rmseMW", "biasMW"):
                    self.assertIsNone(metrics[name])

    def test_non_finite_generation_is_rejected(self):
        for field in (self.forecast, self.actual):
            original = field["generation"]
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(value=value):
                    field["generation"] = value
                    with self.assertRaisesRegex(ValueError, "finite"):
                        compare_forecasts([self.forecast], [self.actual])
            field["generation"] = original
