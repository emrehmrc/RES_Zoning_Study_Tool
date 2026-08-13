import unittest

import pandas as pd

from standalone_solar_scoring import (
    CRITERION_BINDINGS,
    ExcelCell,
    excel_weight_to_percent,
    normalize_solar_values,
    read_levels,
    score_dataframe,
    score_levels,
)


class StandaloneSolarScoringTests(unittest.TestCase):
    def test_level_boundaries_use_first_matching_level(self):
        values = pd.Series([0, 5, 10, 15, 16])
        levels = [
            {"min": 0, "max": 5, "score": 100},
            {"min": 5, "max": 10, "score": 70},
            {"min": 10, "max": 15, "score": 40},
            {"min": 15, "max": 99999, "score": 0},
        ]

        self.assertEqual(score_levels(values, levels).tolist(), [100, 100, 70, 40, 0])

    def test_dashboard_knockout_and_hard_exclusion_behavior(self):
        dataframe = pd.DataFrame(
            {
                "cell_id": [1, 2, 3],
                "distance": [10.0, 10.0, 0.1],
                "coverage": [0.0, 6.0, 0.0],
                "resource": [90.0, 90.0, 90.0],
                "hard_limit": [1.0, 1.0, 11.0],
            }
        )
        layers = [
            {
                "name": "Distance layer",
                "type": "distance_coverage",
                "distance_column": "distance",
                "coverage_column": "coverage",
                "max_coverage_threshold": 5,
                "weight_percent": 50,
                "levels": [
                    {"min": 1, "max": 99999, "score": 100},
                    {"min": 0, "max": 1, "score": 0},
                ],
            },
            {
                "name": "Resource",
                "type": "single_mode",
                "column": "resource",
                "weight_percent": 50,
                "levels": [
                    {"min": 80, "max": 100, "score": 100},
                    {"min": 0, "max": 80, "score": 0},
                ],
            },
        ]
        exclusions = [
            {"name": "Hard limit", "column": "hard_limit", "threshold": 10},
        ]

        results, tracking = score_dataframe(dataframe, layers, exclusions)

        self.assertEqual(results["FINAL_GRID_SCORE"].tolist(), [100.0, 0.0, 0.0])
        self.assertIn("cov>5%", results.loc[1, "EXCLUSION_REASONS"])
        self.assertIn("Hard limit", results.loc[2, "EXCLUSION_REASONS"])
        self.assertEqual(tracking[0]["excluded_count"], 1)

    def test_excel_percentage_weight_is_converted_to_percentage_points(self):
        cell = ExcelCell(0.14, "0.0%")
        self.assertAlmostEqual(
            excel_weight_to_percent(cell, "Temperature weight"),
            14.0,
        )

    def test_excel_levels_skip_fully_blank_level_groups(self):
        cells = {
            "H3": ExcelCell(99999),
            "I3": ExcelCell(0.1),
            "J3": ExcelCell(100),
            "Q3": ExcelCell(0),
            "R3": ExcelCell(0),
            "S3": ExcelCell(0),
        }

        levels = read_levels(cells, 3, "Agricultural Areas")

        self.assertEqual(
            levels,
            [
                {"max": 99999.0, "min": 0.1, "score": 100.0},
                {"max": 0.0, "min": 0.0, "score": 0.0},
            ],
        )

    def test_solar_percentage_input_is_converted_to_excel_ratio(self):
        values = pd.Series([90.0, 80.0, 65.0])
        config = {
            "name": "Solar",
            "levels": [
                {"min": 0.9, "max": 1.0, "score": 100},
                {"min": 0.8, "max": 0.9, "score": 70},
            ],
        }

        normalized = normalize_solar_values(values, config)

        self.assertEqual(normalized.tolist(), [0.9, 0.8, 0.65])

    def test_dust_concentration_binding_uses_mean_column(self):
        dust_bindings = [
            binding
            for binding in CRITERION_BINDINGS
            if binding["name"] == "Dust Concentration"
        ]

        self.assertEqual(len(dust_bindings), 1)
        self.assertEqual(dust_bindings[0]["column"], "Dust_mean")


if __name__ == "__main__":
    unittest.main()
