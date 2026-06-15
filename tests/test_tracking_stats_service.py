import pickle

import pytest

from src.services.tracking_stats_service import (
    bgr_to_hex,
    compute_team_distance_totals,
    extract_team_colors,
    format_distance_meters,
    has_distance_data,
    resolve_tracking_stub_paths,
)


def _sample_tracks():
    return {
        "players": [
            {
                1: {
                    "distance": 100.0,
                    "team_id": 1,
                    "team_color": (255, 0, 0),
                },
                2: {
                    "distance": 50.0,
                    "team_id": 2,
                    "team_color": (0, 0, 255),
                },
            },
            {
                1: {
                    "distance": 250.0,
                    "team_id": 1,
                    "team_color": (255, 0, 0),
                },
                2: {
                    "distance": 180.0,
                    "team_id": 2,
                    "team_color": (0, 0, 255),
                },
            },
        ]
    }


class TestComputeTeamDistanceTotals:
    def test_sums_max_distance_per_player_by_team(self):
        totals = compute_team_distance_totals(_sample_tracks())
        assert totals[1] == pytest.approx(250.0)
        assert totals[2] == pytest.approx(180.0)

    def test_ignores_team_zero(self):
        tracks = {
            "players": [
                {9: {"distance": 500.0, "team_id": 0}},
            ]
        }
        totals = compute_team_distance_totals(tracks)
        assert totals[1] == 0.0
        assert totals[2] == 0.0

    def test_returns_empty_for_invalid_input(self):
        assert compute_team_distance_totals(None) == {}
        assert compute_team_distance_totals({}) == {}


class TestTrackingHelpers:
    def test_bgr_to_hex(self):
        assert bgr_to_hex((255, 128, 0)) == "#0080ff"

    def test_format_distance_meters_short(self):
        assert format_distance_meters(523.7) == "524 m"

    def test_format_distance_meters_long(self):
        result = format_distance_meters(4500)
        assert "km" in result
        assert "4 500 m" in result

    def test_has_distance_data(self):
        assert has_distance_data(_sample_tracks()) is True
        assert has_distance_data({"players": [{}]}) is False

    def test_extract_team_colors(self):
        colors = extract_team_colors(_sample_tracks())
        assert colors[1] == "#0000ff"
        assert colors[2] == "#ff0000"

    def test_resolve_tracking_stub_paths(self, monkeypatch, tmp_path):
        stubs_dir = tmp_path / "stubs"
        stubs_dir.mkdir()
        monkeypatch.setattr(
            "src.services.tracking_stats_service.STUBS_DIR", stubs_dir
        )
        paths = resolve_tracking_stub_paths("output_video_2.mp4")
        assert paths[0] == stubs_dir / "video_2_processed.pkl"

    def test_load_tracking_stub_from_file(self, monkeypatch, tmp_path):
        stubs_dir = tmp_path / "stubs"
        stubs_dir.mkdir()
        stub_path = stubs_dir / "video_2_processed.pkl"
        with open(stub_path, "wb") as f:
            pickle.dump(_sample_tracks(), f)

        monkeypatch.setattr(
            "src.services.tracking_stats_service.STUBS_DIR", stubs_dir
        )

        from src.services.tracking_stats_service import load_tracking_stub

        tracks, path = load_tracking_stub("output_video_2.mp4")
        assert tracks is not None
        assert path == stub_path
