"""Warstwa logiki biznesowej: wczytywanie i normalizacja danych meczowych."""

import json
from pathlib import Path

import pandas as pd

from src.config.paths import (
    MATCH_CSV_PATH,
    MATCH_INCREMENTAL_JSON_PATH,
    MATCH_JSON_PATH,
    OUTPUT_DIR,
    PLACEHOLDER_MATCH,
)


def flatten_match_to_row(match: dict) -> dict:
    row = {
        "Id": match.get("Id"),
        "Date": match.get("Date"),
        "Time": match.get("Time"),
        "League": match.get("League"),
        "Round": match.get("Round"),
        "Home": match.get("Home"),
        "Away": match.get("Away"),
        "Home_Score": match.get("Home_Score"),
        "Away_Score": match.get("Away_Score"),
        "Best_Odd_1_FT": match.get("Best_Odd_1_FT"),
        "Best_Odd_X_FT": match.get("Best_Odd_X_FT"),
        "Best_Odd_2_FT": match.get("Best_Odd_2_FT"),
    }
    stats_ft = match.get("Statistics_FT", {})
    for stat_name, values in stats_ft.items():
        row[f"Home_{stat_name}"] = values.get("Home")
        row[f"Away_{stat_name}"] = values.get("Away")
    return row


def load_matches_from_json(json_path: Path) -> list[dict]:
    if not json_path.exists() or json_path.stat().st_size == 0:
        return []
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [m for m in data if isinstance(m, dict)]
        if isinstance(data, dict):
            return [data]
    except (json.JSONDecodeError, OSError):
        pass
    return []


def build_match_label(home: str, away: str, date, pair_count: int) -> str:
    base = f"{home} - {away}"
    if pair_count > 1 and pd.notna(date):
        return f"{base} ({date})"
    return base


def scan_match_files() -> pd.DataFrame:
    """Skanuje data/output/ i łączy mecze z CSV oraz plików JSON."""
    matches_by_id: dict[str, dict] = {}

    for json_path in (MATCH_JSON_PATH, MATCH_INCREMENTAL_JSON_PATH):
        for match in load_matches_from_json(json_path):
            match_id = match.get("Id")
            key = str(match_id) if match_id else None
            if key:
                matches_by_id[key] = match
            elif match.get("Home") and match.get("Away"):
                fallback_key = (
                    f"{match['Home']}|{match['Away']}|{match.get('Date', '')}"
                )
                matches_by_id[fallback_key] = match

    if OUTPUT_DIR.exists():
        for json_path in sorted(OUTPUT_DIR.glob("*.json")):
            if json_path.name in {
                MATCH_JSON_PATH.name,
                MATCH_INCREMENTAL_JSON_PATH.name,
            }:
                continue
            for match in load_matches_from_json(json_path):
                match_id = match.get("Id")
                if match_id:
                    matches_by_id[str(match_id)] = match

    if MATCH_CSV_PATH.exists() and MATCH_CSV_PATH.stat().st_size > 0:
        try:
            csv_df = pd.read_csv(MATCH_CSV_PATH)
            if (
                not csv_df.empty
                and "Home" in csv_df.columns
                and "Away" in csv_df.columns
            ):
                for _, row in csv_df.iterrows():
                    row_dict = row.to_dict()
                    match_id = row_dict.get("Id")
                    key = str(match_id) if pd.notna(match_id) else None
                    if key and key not in matches_by_id:
                        matches_by_id[key] = row_dict
                    elif not key:
                        fallback_key = (
                            f"{row_dict.get('Home')}|{row_dict.get('Away')}|"
                            f"{row_dict.get('Date', '')}"
                        )
                        if fallback_key not in matches_by_id:
                            matches_by_id[fallback_key] = row_dict
        except (pd.errors.EmptyDataError, OSError):
            pass

    if not matches_by_id:
        return pd.DataFrame()

    rows = []
    for match in matches_by_id.values():
        if isinstance(match, dict) and "Statistics_FT" in match:
            rows.append(flatten_match_to_row(match))
        elif isinstance(match, dict):
            rows.append(match)

    df = pd.DataFrame(rows)
    if df.empty or "Home" not in df.columns or "Away" not in df.columns:
        return pd.DataFrame()

    if "Date" in df.columns:
        df = df.sort_values(by=["Date", "Time"], ascending=False, na_position="last")
    return df.drop_duplicates(
        subset=["Home", "Away", "Date"], keep="first"
    ).reset_index(drop=True)


def build_match_choices(df: pd.DataFrame) -> list[str]:
    if df.empty or "Home" not in df.columns or "Away" not in df.columns:
        return []

    pair_counts = df.groupby(["Home", "Away"], dropna=False).size()
    labels = []
    seen = set()

    for _, row in df.iterrows():
        label = build_match_label(
            row["Home"],
            row["Away"],
            row.get("Date"),
            pair_counts.get((row["Home"], row["Away"]), 1),
        )
        if label not in seen:
            labels.append(label)
            seen.add(label)
    return labels


def filter_df_by_match_label(df: pd.DataFrame, selected: str) -> pd.DataFrame:
    if df.empty or not selected or selected == PLACEHOLDER_MATCH:
        return df

    pair_counts = df.groupby(["Home", "Away"], dropna=False).size()
    for _, row in df.iterrows():
        label = build_match_label(
            row["Home"],
            row["Away"],
            row.get("Date"),
            pair_counts.get((row["Home"], row["Away"]), 1),
        )
        if label == selected:
            return df.loc[[row.name]]
    return pd.DataFrame()
