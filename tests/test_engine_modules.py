import numpy as np
import pytest

from player_ball_assigner.player_ball_assigner import PlayerBallAssigner
from team_assigner.team_assigner import TeamAssigner
from utils.bbox_utils import (
    get_bbox_width,
    get_center_of_bbox,
    get_foot_position,
    measure_distance,
    measure_xy_distance,
)
from view_transformer.view_transformer import ViewTransformer


class TestBboxUtils:
    def test_get_center_of_bbox(self):
        assert get_center_of_bbox([100, 200, 300, 400]) == (200, 300)

    def test_get_foot_position(self):
        assert get_foot_position([100, 200, 300, 400]) == (200, 400)

    def test_get_bbox_width(self):
        assert get_bbox_width([10, 0, 50, 100]) == 40

    def test_measure_distance(self):
        assert measure_distance((0, 0), (3, 4)) == pytest.approx(5.0)

    def test_measure_xy_distance(self):
        assert measure_xy_distance((10, 20), (4, 8)) == (6, 12)


class TestPlayerBallAssigner:
    def setup_method(self):
        self.assigner = PlayerBallAssigner()

    def test_assigns_nearest_player_within_threshold(self):
        players = {
            1: {"bbox": [100, 100, 120, 200]},
            2: {"bbox": [300, 100, 320, 200]},
        }
        # Piłka blisko stóp zawodnika 1 (algorytm mierzy od dolnej krawędzi bbox)
        ball_bbox = [108, 190, 112, 198]
        assert self.assigner.assign_ball_to_player(players, ball_bbox) == 1

    def test_returns_minus_one_when_no_player_close(self):
        players = {1: {"bbox": [0, 0, 10, 10]}}
        ball_bbox = [500, 500, 510, 510]
        assert self.assigner.assign_ball_to_player(players, ball_bbox) == -1


class TestTeamAssigner:
    def setup_method(self):
        self.assigner = TeamAssigner()

    def test_choose_cluster_count_for_large_squad(self):
        assert self.assigner._choose_cluster_count(22) == 4

    def test_choose_cluster_count_for_small_squad(self):
        assert self.assigner._choose_cluster_count(3) == 3

    def test_nearest_team_id_prefers_closer_color(self):
        self.assigner.team_colors[1] = np.array([0, 0, 255])
        self.assigner.team_colors[2] = np.array([255, 0, 0])
        assert self.assigner._nearest_team_id(np.array([10, 0, 240])) == 1
        assert self.assigner._nearest_team_id(np.array([240, 0, 10])) == 2

    def test_outlier_color_detected_when_far_from_both_teams(self):
        self.assigner.team_colors[1] = np.array([0, 0, 255])
        self.assigner.team_colors[2] = np.array([255, 0, 0])
        self.assigner.outlier_distance_threshold = 50.0
        assert self.assigner._is_outlier_color(np.array([0, 255, 0])) is True

    def test_color_distance_is_zero_for_identical_colors(self):
        color = np.array([10, 20, 30])
        assert TeamAssigner._color_distance(color, color) == pytest.approx(0.0)


class TestViewTransformer:
    def setup_method(self):
        self.transformer = ViewTransformer()

    def test_point_outside_pitch_returns_none(self):
        assert self.transformer.transform_point(np.array([0, 0])) is None

    def test_point_inside_pitch_returns_coordinates(self):
        point = np.array([500, 600])
        result = self.transformer.transform_point(point)
        assert result is not None
        assert result.shape == (1, 2)
