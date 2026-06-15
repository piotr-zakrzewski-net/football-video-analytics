"""Komponenty widoku Shiny (warstwa prezentacji)."""

from shiny import ui

from src.services.stats_formatters import compute_bar_percentages
from src.services.tracking_stats_service import (
    contrast_text_color,
    format_distance_meters,
)


def draw_stat_bar(stat_name, home_val, away_val):
    h_pct, a_pct = compute_bar_percentages(home_val, away_val)

    return ui.div(
        ui.div(
            ui.span(
                str(home_val),
                style="font-weight: bold; font-size: 1.2em; color: #0d6efd;",
            ),
            ui.span(
                stat_name,
                style=(
                    "font-weight: bold; color: #495057; font-size: 0.8em; "
                    "text-transform: uppercase; white-space: nowrap; margin: 0 10px"
                ),
            ),
            ui.span(
                str(away_val),
                style="font-weight: bold; font-size: 1.2em; color: #dc3545;",
            ),
            style=(
                "display: flex; justify-content: space-between; align-items: center; "
                "margin-bottom: 5px; margin-top: 15px;"
            ),
        ),
        ui.div(
            ui.div(
                style=(
                    f"width: {h_pct}%; background-color: #0d6efd; height: 10px; "
                    "border-radius: 5px 0 0 5px; transition: width 0.5s;"
                )
            ),
            ui.div(
                style=(
                    f"width: {a_pct}%; background-color: #dc3545; height: 10px; "
                    "border-radius: 0 5px 5px 0; transition: width 0.5s;"
                )
            ),
            style=(
                "display: flex; width: 100%; background-color: #e9ecef; "
                "border-radius: 5px;"
            ),
        ),
    )


def build_team_distance_box(team_label: str, distance_m: float, bg_hex: str):
    text_color = contrast_text_color(bg_hex)
    return ui.div(
        ui.div(
            team_label,
            style=(
                f"font-weight: bold; font-size: 1.1em; text-align: center; "
                f"color: {text_color}; margin-bottom: 0.5rem;"
            ),
        ),
        ui.div(
            format_distance_meters(distance_m),
            style=(
                f"font-size: 1.75em; font-weight: bold; text-align: center; "
                f"color: {text_color};"
            ),
        ),
        style=(
            f"background-color: {bg_hex}; border-radius: 8px; padding: 1.25rem; "
            "box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.075); min-height: 120px; "
            "display: flex; flex-direction: column; justify-content: center;"
        ),
    )
