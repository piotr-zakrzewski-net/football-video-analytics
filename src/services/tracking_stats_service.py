"""Warstwa logiki biznesowej: statystyki dystansu z plików trackingu (.pkl)."""

import pickle
from pathlib import Path

from src.config.paths import STUBS_DIR


def resolve_tracking_stub_paths(video_filename: str) -> list[Path]:
    """Mapuje plik wideo (np. output_video_2.mp4) na możliwe pliki .pkl."""
    stem = Path(video_filename).stem
    base_stem = stem[len("output_") :] if stem.startswith("output_") else stem
    candidates = [
        STUBS_DIR / f"{base_stem}_processed.pkl",
        STUBS_DIR / f"{base_stem}_stub.pkl",
        STUBS_DIR / f"{stem}_processed.pkl",
        STUBS_DIR / f"{stem}_stub.pkl",
    ]
    unique_paths = []
    seen = set()
    for path in candidates:
        key = str(path)
        if key not in seen:
            unique_paths.append(path)
            seen.add(key)
    return unique_paths


def count_player_distance_entries(tracks) -> int:
    players = tracks.get("players") if isinstance(tracks, dict) else None
    if not isinstance(players, list):
        return 0

    count = 0
    for frame in players:
        if not isinstance(frame, dict):
            continue
        for player_data in frame.values():
            if (
                isinstance(player_data, dict)
                and player_data.get("distance") is not None
            ):
                count += 1
    return count


def enrich_tracks_with_distance(tracks):
    """Uzupełnia dystans w pamięci, jeśli w pliku jest position_transformed."""
    if count_player_distance_entries(tracks) > 0:
        return tracks

    players = tracks.get("players") if isinstance(tracks, dict) else None
    if not isinstance(players, list):
        return tracks

    has_transformed = any(
        isinstance(player_data, dict)
        and player_data.get("position_transformed") is not None
        for frame in players
        if isinstance(frame, dict)
        for player_data in frame.values()
    )
    if not has_transformed:
        return tracks

    try:
        from speed_and_distance_estimator import SpeedAndDistance_Estimator

        SpeedAndDistance_Estimator().add_speed_and_distance_to_tracks(tracks)
    except Exception:
        pass
    return tracks


def load_tracking_stub(video_filename: str):
    best_tracks = None
    best_path = None
    best_score = -1

    for stub_path in resolve_tracking_stub_paths(video_filename):
        if not stub_path.exists() or stub_path.stat().st_size == 0:
            continue
        try:
            with open(stub_path, "rb") as f:
                tracks = pickle.load(f)
            tracks = enrich_tracks_with_distance(tracks)
            score = count_player_distance_entries(tracks)
            if score > best_score:
                best_score = score
                best_tracks = tracks
                best_path = stub_path
        except (OSError, pickle.UnpicklingError):
            continue

    if best_tracks is None:
        expected = resolve_tracking_stub_paths(video_filename)[0]
        return None, expected
    return best_tracks, best_path


def compute_team_distance_totals(tracks) -> dict[int, float]:
    """
    tracks['players'] to lista klatek; każda klatka to {player_id: {...}}.
    Dla każdego zawodnika śledzi maks. dystans i przypisanie do drużyny.
    """
    if not isinstance(tracks, dict):
        return {}

    players = tracks.get("players")
    if not isinstance(players, list):
        return {}

    player_teams = {}
    player_max_distance = {}

    for frame in players:
        if not isinstance(frame, dict):
            continue

        for player_id, player_data in frame.items():
            if not isinstance(player_data, dict):
                continue

            team_id = player_data.get("team_id")
            if team_id is not None:
                try:
                    player_teams[player_id] = int(team_id)
                except (TypeError, ValueError):
                    pass

            distance = player_data.get("distance", 0)
            try:
                distance_float = float(distance)
            except (TypeError, ValueError):
                distance_float = 0.0

            if distance_float > player_max_distance.get(player_id, 0.0):
                player_max_distance[player_id] = distance_float

    team_totals = {1: 0.0, 2: 0.0}
    for player_id, max_distance in player_max_distance.items():
        team_id = player_teams.get(player_id)
        if team_id in team_totals and max_distance > 0:
            team_totals[team_id] += max_distance

    return team_totals


def has_distance_data(tracks) -> bool:
    return any(
        isinstance(frame, dict)
        and any(
            isinstance(player_data, dict)
            and float(player_data.get("distance", 0) or 0) > 0
            for player_data in frame.values()
        )
        for frame in tracks.get("players", [])
    )


DEFAULT_TEAM_COLORS = {1: "#0d6efd", 2: "#dc3545"}


def bgr_to_hex(color) -> str:
    try:
        channels = list(color)[:3]
        b, g, r = (int(c) for c in channels)
        return f"#{r:02x}{g:02x}{b:02x}"
    except (TypeError, ValueError, IndexError):
        return "#808080"


def extract_team_colors(tracks) -> dict:
    colors = DEFAULT_TEAM_COLORS.copy()
    if not isinstance(tracks, dict):
        return colors

    players = tracks.get("players")
    if not isinstance(players, list):
        return colors

    found_teams = set()
    for frame in players:
        if not isinstance(frame, dict):
            continue
        for player_data in frame.values():
            if not isinstance(player_data, dict):
                continue
            team_id = player_data.get("team_id")
            team_color = player_data.get("team_color")
            if team_id is None or team_color is None:
                continue
            try:
                tid = int(team_id)
            except (TypeError, ValueError):
                continue
            if tid in (1, 2) and tid not in found_teams:
                colors[tid] = bgr_to_hex(team_color)
                found_teams.add(tid)
        if found_teams == {1, 2}:
            break

    return colors


def format_distance_meters(distance: float) -> str:
    meters = round(float(distance))
    if meters >= 1000:
        return f"{meters / 1000:.1f} km ({meters:,} m)".replace(",", " ")
    return f"{meters} m"


def contrast_text_color(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except (ValueError, IndexError):
        return "#ffffff"
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#ffffff" if luminance < 0.55 else "#212529"
