"""Czyste funkcje formatujące statystyki (bez zależności od UI)."""

import pandas as pd


def extract_numeric_stat(val) -> float:
    if pd.isna(val) or val == "":
        return 0.0
    val_str = str(val).replace("%", "").split("(")[0].strip()
    try:
        return float(val_str)
    except ValueError:
        return 0.0


def compute_bar_percentages(home_val, away_val) -> tuple[float, float]:
    h_num = extract_numeric_stat(home_val)
    a_num = extract_numeric_stat(away_val)
    total = abs(h_num) + abs(a_num)
    if total > 0:
        return abs(h_num) / total * 100, abs(a_num) / total * 100
    return 50.0, 50.0


def format_percentage_stat(val) -> str:
    return f"{int(float(val) * 100)}%"


def format_integer_stat(val) -> str:
    fval = float(val)
    return str(int(fval)) if fval.is_integer() else str(val)
