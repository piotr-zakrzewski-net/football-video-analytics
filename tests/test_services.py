import json

import pandas as pd
import pytest

from src.services.match_data_service import (
    build_match_choices,
    build_match_label,
    filter_df_by_match_label,
    flatten_match_to_row,
    scan_match_files,
)
from src.services.stats_formatters import (
    compute_bar_percentages,
    extract_numeric_stat,
    format_integer_stat,
    format_percentage_stat,
)


class TestFlattenMatchToRow:
    def test_flattens_statistics_ft(self):
        match = {
            "Id": "abc",
            "Home": "Team A",
            "Away": "Team B",
            "Statistics_FT": {
                "Ball possession": {"Home": 0.55, "Away": 0.45},
                "Total shots": {"Home": 12, "Away": 8},
            },
        }
        row = flatten_match_to_row(match)
        assert row["Home_Ball possession"] == 0.55
        assert row["Away_Total shots"] == 8


class TestBuildMatchLabel:
    def test_unique_pair_without_date(self):
        assert build_match_label("A", "B", None, 1) == "A - B"

    def test_duplicate_pair_includes_date(self):
        assert build_match_label("A", "B", "2024-01-01", 2) == "A - B (2024-01-01)"


class TestMatchChoicesAndFilter:
    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame(
            [
                {"Home": "A", "Away": "B", "Date": "2024-01-01"},
                {"Home": "C", "Away": "D", "Date": "2024-02-01"},
            ]
        )

    def test_build_match_choices(self, sample_df):
        choices = build_match_choices(sample_df)
        assert choices == ["A - B", "C - D"]

    def test_filter_df_by_match_label(self, sample_df):
        filtered = filter_df_by_match_label(sample_df, "C - D")
        assert len(filtered) == 1
        assert filtered.iloc[0]["Home"] == "C"


class TestScanMatchFiles:
    def test_scan_empty_directory(self, tmp_path, monkeypatch):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        monkeypatch.setattr(
            "src.services.match_data_service.OUTPUT_DIR", output_dir
        )
        monkeypatch.setattr(
            "src.services.match_data_service.MATCH_JSON_PATH",
            output_dir / "flashscore_results.json",
        )
        monkeypatch.setattr(
            "src.services.match_data_service.MATCH_INCREMENTAL_JSON_PATH",
            output_dir / "flashscore_incremental.json",
        )
        monkeypatch.setattr(
            "src.services.match_data_service.MATCH_CSV_PATH",
            output_dir / "flashscore_results.csv",
        )

        json_path = output_dir / "flashscore_results.json"
        json_path.write_text(
            json.dumps(
                [
                    {
                        "Id": "1",
                        "Home": "X",
                        "Away": "Y",
                        "Date": "2024-03-01",
                        "Statistics_FT": {
                            "Total shots": {"Home": 5, "Away": 3}
                        },
                    }
                ]
            ),
            encoding="utf-8",
        )

        df = scan_match_files()
        assert not df.empty
        assert df.iloc[0]["Home"] == "X"
        assert df.iloc[0]["Home_Total shots"] == 5


class TestStatsFormatters:
    def test_extract_numeric_stat_handles_percent(self):
        assert extract_numeric_stat("55%") == pytest.approx(55.0)

    def test_extract_numeric_stat_handles_empty(self):
        assert extract_numeric_stat("") == 0.0

    def test_compute_bar_percentages_equal_split_when_zero(self):
        assert compute_bar_percentages(0, 0) == (50.0, 50.0)

    def test_compute_bar_percentages_proportional(self):
        h, a = compute_bar_percentages(30, 70)
        assert h == pytest.approx(30.0)
        assert a == pytest.approx(70.0)

    def test_format_percentage_stat(self):
        assert format_percentage_stat(0.62) == "62%"

    def test_format_integer_stat(self):
        assert format_integer_stat(10.0) == "10"
