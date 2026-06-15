from collections import Counter

import numpy as np
from sklearn.cluster import KMeans


class TeamAssigner:
    def __init__(self):
        self.team_colors = {}
        self.player_team_dict = {}
        self.outlier_distance_threshold = 120.0
        self.main_cluster_ids = set()

    @staticmethod
    def _color_distance(color_a, color_b):
        return float(np.linalg.norm(np.asarray(color_a) - np.asarray(color_b)))

    def get_clustering_model(self, cropped_image):
        pixels = cropped_image.reshape(-1, 3)
        kmeans = KMeans(n_clusters=2, init="k-means++", n_init=1, random_state=42)
        kmeans.fit(pixels)
        return kmeans

    def get_player_color(self, frame, bbox):
        cropped_image = frame[int(bbox[1]) : int(bbox[3]), int(bbox[0]) : int(bbox[2])]
        top_half = cropped_image[0 : int(cropped_image.shape[0] // 2), :]

        kmeans = self.get_clustering_model(top_half)
        labels = kmeans.labels_
        clustered_image = labels.reshape(top_half.shape[0], top_half.shape[1])

        corner_clusters = [
            clustered_image[0, 0],
            clustered_image[0, -1],
            clustered_image[-1, 0],
            clustered_image[-1, -1],
        ]
        non_player_cluster = max(set(corner_clusters), key=corner_clusters.count)
        player_cluster = 1 - non_player_cluster

        return kmeans.cluster_centers_[player_cluster]

    def _choose_cluster_count(self, n_players):
        """Więcej klastrów niż 2, aby bramkarz nie stał się centroidem drużyny."""
        if n_players < 4:
            return max(2, n_players)
        return min(4, max(3, n_players // 5))

    def _nearest_team_id(self, player_color):
        dist_1 = self._color_distance(player_color, self.team_colors[1])
        dist_2 = self._color_distance(player_color, self.team_colors[2])
        return 1 if dist_1 <= dist_2 else 2

    def _is_outlier_color(self, player_color):
        if 1 not in self.team_colors or 2 not in self.team_colors:
            return False

        min_dist = min(
            self._color_distance(player_color, self.team_colors[1]),
            self._color_distance(player_color, self.team_colors[2]),
        )
        return min_dist > self.outlier_distance_threshold

    def assign_team_color(self, frame, player_detections):
        player_ids = []
        player_colors = []

        for player_id, player_detection in player_detections.items():
            bbox = player_detection["bbox"]
            color = self.get_player_color(frame, bbox)
            player_ids.append(player_id)
            player_colors.append(color)

        player_colors = np.asarray(player_colors)
        n_players = len(player_colors)

        if n_players == 0:
            return

        if n_players == 1:
            self.team_colors[1] = player_colors[0]
            self.team_colors[2] = player_colors[0]
            self.player_team_dict[player_ids[0]] = 1
            return

        n_clusters = self._choose_cluster_count(n_players)
        kmeans = KMeans(
            n_clusters=n_clusters, init="k-means++", n_init=10, random_state=42
        )
        labels = kmeans.fit_predict(player_colors)

        cluster_sizes = Counter(labels)
        main_cluster_ids = [
            cluster_id for cluster_id, _ in cluster_sizes.most_common(2)
        ]
        self.main_cluster_ids = set(main_cluster_ids)

        self.team_colors[1] = kmeans.cluster_centers_[main_cluster_ids[0]]
        self.team_colors[2] = kmeans.cluster_centers_[main_cluster_ids[1]]
        self.kmeans = kmeans

        inlier_distances = []
        for color, label in zip(player_colors, labels):
            if label in self.main_cluster_ids:
                team_id = main_cluster_ids.index(label) + 1
                inlier_distances.append(
                    self._color_distance(color, self.team_colors[team_id])
                )

        if inlier_distances:
            self.outlier_distance_threshold = max(
                float(np.median(inlier_distances) * 2.5), 40.0
            )

        for player_id, color, label in zip(player_ids, player_colors, labels):
            if label in self.main_cluster_ids:
                team_id = main_cluster_ids.index(label) + 1
            else:
                # Bramkarze i inne anomalie: najbliższa z dwóch głównych drużyn.
                team_id = self._nearest_team_id(color)
            self.player_team_dict[player_id] = team_id

    def get_player_team(self, frame, player_bbox, player_id):
        if player_id in self.player_team_dict:
            return self.player_team_dict[player_id]

        player_color = self.get_player_color(frame, player_bbox)

        if self._is_outlier_color(player_color):
            team_id = 0
        else:
            team_id = self._nearest_team_id(player_color)

        self.player_team_dict[player_id] = team_id
        return team_id
