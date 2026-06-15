import os

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from shiny import render, reactive, ui

from src.config.paths import OUTPUT_DIR, PLACEHOLDER_MATCH
from src.dashboard.components import build_team_distance_box, draw_stat_bar
from src.scraper import FlashScoreScraper
from src.services.match_data_service import (
    build_match_choices,
    filter_df_by_match_label,
    scan_match_files,
)
from src.services.stats_formatters import format_integer_stat, format_percentage_stat
from src.services.tracking_stats_service import (
    DEFAULT_TEAM_COLORS,
    compute_team_distance_totals,
    extract_team_colors,
    has_distance_data,
    load_tracking_stub,
)


def server(input, output, session):
    data_version = reactive.Value(0)

    @reactive.calc
    def fetch_raw_data():
        data_version.get()
        df = scan_match_files()
        if df.empty:
            return pd.DataFrame({"Błąd": ["Brak pobranych meczów w data/output/."]})
        return df

    @reactive.calc
    def available_matches():
        df = fetch_raw_data()
        if df.empty or "Błąd" in df.columns:
            return []
        return build_match_choices(df)

    @reactive.Effect
    def update_match_list():
        choices = available_matches()
        current = input.match_selector()

        if choices:
            selected = current if current in choices else choices[0]
            ui.update_select("match_selector", choices=choices, selected=selected)
        else:
            ui.update_select(
                "match_selector",
                choices=[PLACEHOLDER_MATCH],
                selected=PLACEHOLDER_MATCH,
            )

    @reactive.calc
    def load_data():
        df = fetch_raw_data()
        selected = input.match_selector()
        if (
            df.empty
            or "Błąd" in df.columns
            or not selected
            or selected == PLACEHOLDER_MATCH
        ):
            return df
        filtered_df = filter_df_by_match_label(df, selected)
        return filtered_df if not filtered_df.empty else df

    @reactive.Effect
    @reactive.event(input.btn_reload)
    def reload_data():
        data_version.set(data_version.get() + 1)
        match_count = len(build_match_choices(scan_match_files()))
        print(
            f"[SCRAPER] Odświeżono listę meczów z data/output/ ({match_count} spotkań)."
        )
        if match_count:
            ui.notification_show(
                f"Wczytano {match_count} spotkań z plików danych.",
                type="message",
            )
        else:
            ui.notification_show(
                "Nie znaleziono pobranych meczów w data/output/.",
                type="warning",
            )

    @reactive.Effect
    @reactive.event(input.btn_scrape)
    def run_scraper():
        url = input.url_input()
        print(f"[SCRAPER] Przycisk 'Pobierz dane' kliknięty. URL: {url!r}")

        if not url or not url.strip():
            print("[SCRAPER] Brak URL — przerywam.")
            ui.notification_show("Wklej link do meczu z Flashscore.", type="warning")
            return

        scraper = None
        try:
            with ui.Progress(min=0, max=1) as p:
                p.set(message="Pobieranie danych z Flashscore...", value=0)
                scraper = FlashScoreScraper(headless=True)
                p.set(value=0.3)
                scraper.scrape_from_url(url.strip())
                scraper.save_results()
                p.set(value=1, message="Gotowe!")
            print("[SCRAPER] Scrapowanie zakończone pomyślnie.")
            ui.notification_show("Dane pobrane i zapisane.", type="message")
        except Exception as e:
            print(f"[SCRAPER] Błąd podczas scrapowania: {e}")
            import traceback

            traceback.print_exc()
            ui.notification_show(f"Błąd scrapowania: {e}", type="error")
        finally:
            if scraper is not None:
                scraper.close()
            data_version.set(data_version.get() + 1)
            print("[SCRAPER] Wymuszono odświeżenie danych w dashboardzie.")

    @render.text
    def match_title():
        df = load_data()
        if "League" in df.columns and "Round" in df.columns:
            return f"{df['League'].iloc[0]} | {df['Round'].iloc[0]}"
        return "Brak danych"

    @render.text
    def home_team_name():
        df = load_data()
        return (
            f"Gospodarze: {df['Home'].iloc[0]}"
            if "Home" in df.columns
            else "Gospodarze"
        )

    @render.text
    def away_team_name():
        df = load_data()
        return f"Goście: {df['Away'].iloc[0]}" if "Away" in df.columns else "Goście"

    @render.text
    def home_team_score():
        df = load_data()
        return (
            f"{int(df['Home_Score'].iloc[0])}"
            if "Home_Score" in df.columns and pd.notna(df["Home_Score"].iloc[0])
            else "-"
        )

    @render.text
    def away_team_score():
        df = load_data()
        return (
            f"{int(df['Away_Score'].iloc[0])}"
            if "Away_Score" in df.columns and pd.notna(df["Away_Score"].iloc[0])
            else "-"
        )

    @render.text
    def match_date():
        df = load_data()
        return (
            f"{df['Date'].iloc[0]} ({df['Time'].iloc[0]})"
            if "Date" in df.columns
            else "-"
        )

    @render.text
    def odd_1():
        df = load_data()
        return (
            f"{df['Best_Odd_1_FT'].iloc[0]}"
            if "Best_Odd_1_FT" in df.columns and pd.notna(df["Best_Odd_1_FT"].iloc[0])
            else "-"
        )

    @render.text
    def odd_x():
        df = load_data()
        return (
            f"{df['Best_Odd_X_FT'].iloc[0]}"
            if "Best_Odd_X_FT" in df.columns and pd.notna(df["Best_Odd_X_FT"].iloc[0])
            else "-"
        )

    @render.text
    def odd_2():
        df = load_data()
        return (
            f"{df['Best_Odd_2_FT'].iloc[0]}"
            if "Best_Odd_2_FT" in df.columns and pd.notna(df["Best_Odd_2_FT"].iloc[0])
            else "-"
        )

    def generate_bars_for_group(df, stats_dict):
        if df.empty or "Błąd" in df.columns:
            return ui.p("Brak danych.", style="color: gray;")
        elements = []
        percentage_stats = [
            "Ball possession",
            "Passes",
            "Long passes",
            "Passes in final third",
            "Crosses",
            "Tackles",
        ]
        for original_name, pl_name in stats_dict.items():
            home_col, away_col = f"Home_{original_name}", f"Away_{original_name}"
            if home_col in df.columns and away_col in df.columns:
                h_val, a_val = df[home_col].iloc[0], df[away_col].iloc[0]
                if pd.notna(h_val) and pd.notna(a_val):
                    if original_name in percentage_stats:
                        h_val_display = format_percentage_stat(h_val)
                        a_val_display = format_percentage_stat(a_val)
                    else:
                        h_val_display = format_integer_stat(h_val)
                        a_val_display = format_integer_stat(a_val)
                    elements.append(
                        draw_stat_bar(pl_name, h_val_display, a_val_display)
                    )
        return (
            ui.div(*elements)
            if elements
            else ui.p("Brak statystyk.", style="color: gray;")
        )

    @render.ui
    def stats_main():
        return generate_bars_for_group(
            load_data(),
            {
                "Ball possession": "Posiadanie piłki",
                "Expected goals (xG)": "Oczekiwane gole (xG)",
                "Total shots": "Strzały ogółem",
                "Shots on target": "Strzały celne",
                "Big chances": "Wielkie szanse",
                "Corner kicks": "Rzuty rożne",
            },
        )

    @render.ui
    def stats_attack():
        return generate_bars_for_group(
            load_data(),
            {
                "xG on target (xGOT)": "Oczekiwane gole celne (xGOT)",
                "Shots off target": "Strzały niecelne",
                "Blocked shots": "Zablokowane strzały",
                "Shots inside the box": "Strzały z pola karnego",
                "Shots outside the box": "Strzały z dystansu",
                "Hit the woodwork": "Słupki / Poprzeczki",
                "Headed goals": "Gole głową",
                "Touches in opposition box": "Kontakty w polu karnym rywala",
                "Offsides": "Spalone",
            },
        )

    @render.ui
    def stats_passing():
        return generate_bars_for_group(
            load_data(),
            {
                "Passes": "Skuteczność podań",
                "Accurate through passes": "Celne prostopadłe",
                "Long passes": "Skuteczność długich podań",
                "Passes in final third": "Podania w ostatniej tercji",
                "Crosses": "Skuteczność dośrodkowań",
                "Expected assists (xA)": "Oczekiwane asysty (xA)",
                "Free kicks": "Rzuty wolne",
                "Throw ins": "Rzuty z autu",
            },
        )

    @render.ui
    def stats_defense():
        return generate_bars_for_group(
            load_data(),
            {
                "Tackles": "Skuteczność odbiorów",
                "Duels won": "Wygrane pojedynki",
                "Clearances": "Wybicia",
                "Interceptions": "Przechwyty",
                "Goalkeeper saves": "Obrony bramkarza",
                "xGOT faced": "xGOT bronione (Zagrożenie)",
                "Goals prevented": "Zapobiegnięto golom",
                "Errors leading to shot": "Błędy -> Strzał",
                "Errors leading to goal": "Błędy -> Gol",
                "Fouls": "Faule",
                "Yellow cards": "Żółte kartki",
                "Red cards": "Czerwone kartki",
            },
        )

    @render.ui
    def radar_chart():
        df = load_data()
        if df.empty or "Błąd" in df.columns:
            return ui.p("Brak danych.")

        home_team, away_team = df["Home"].iloc[0], df["Away"].iloc[0]

        def get_val(col, max_v=20):
            if col in df.columns and pd.notna(df[col].iloc[0]):
                val = float(str(df[col].iloc[0]).replace("%", ""))
                return min(val, max_v)
            return 0

        cats = ["Strzały", "Strzały celne", "Rzuty rożne", "Wielkie szanse"]

        h_vals = [
            get_val("Home_Total shots"),
            get_val("Home_Shots on target"),
            get_val("Home_Corner kicks"),
            get_val("Home_Big chances"),
        ]
        a_vals = [
            get_val("Away_Total shots"),
            get_val("Away_Shots on target"),
            get_val("Away_Corner kicks"),
            get_val("Away_Big chances"),
        ]

        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                r=h_vals + [h_vals[0]],
                theta=cats + [cats[0]],
                fill="toself",
                name=home_team,
                line_color="#0d6efd",
            )
        )
        fig.add_trace(
            go.Scatterpolar(
                r=a_vals + [a_vals[0]],
                theta=cats + [cats[0]],
                fill="toself",
                name=away_team,
                line_color="#dc3545",
            )
        )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 20])),
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5
            ),
            margin=dict(l=60, r=60, t=40, b=40),
        )
        return ui.HTML(pio.to_html(fig, full_html=False))

    @reactive.Effect
    def update_video_list():
        if OUTPUT_DIR.exists():
            videos = sorted(f for f in os.listdir(OUTPUT_DIR) if f.endswith(".mp4"))
            ui.update_select("video_selector", choices=videos)

    @render.ui
    def dynamic_video_player():
        selected = input.video_selector()
        if not selected:
            return ui.p("Brak wideo.")
        return ui.tags.video(
            src=f"/wideo/{selected}",
            type="video/mp4",
            controls=True,
            style="width: 100%; border-radius: 8px; background-color: black;",
        )

    @render.ui
    def distance_stats():
        selected = input.video_selector()
        if not selected:
            return ui.p(
                "Wybierz nagranie, aby zobaczyć statystyki dystansu.",
                style="color: gray; font-style: italic;",
            )

        try:
            tracks, stub_path = load_tracking_stub(selected)
            if tracks is None:
                return ui.p(
                    f"Nie znaleziono pliku trackingu dla „{selected}”. ",
                    ui.tags.br(),
                    f"Oczekiwany plik: {stub_path.name}",
                    style="color: gray;",
                )

            if not has_distance_data(tracks):
                return ui.p(
                    "Brak danych o dystansie w pliku trackingu. ",
                    ui.tags.br(),
                    "Uruchom ponownie ",
                    ui.tags.code("main_process.py"),
                    ", aby wygenerować plik ",
                    ui.tags.code("*_processed.pkl"),
                    ".",
                    style="color: gray; font-style: italic;",
                )

            team_distances = compute_team_distance_totals(tracks)
            team_1_distance = round(team_distances.get(1, 0.0))
            team_2_distance = round(team_distances.get(2, 0.0))
            team_colors = extract_team_colors(tracks)

            if team_1_distance == 0 and team_2_distance == 0:
                return ui.p(
                    "Znaleziono dane o dystansie, ale brak przypisań ",
                    ui.tags.code("team_id"),
                    " dla zawodników. Uruchom ponownie ",
                    ui.tags.code("main_process.py"),
                    ".",
                    style="color: gray; font-style: italic;",
                )

            return ui.div(
                ui.p(
                    f"Źródło: {stub_path.name}",
                    class_="text-muted small mb-3",
                    style="text-align: center;",
                ),
                ui.layout_columns(
                    build_team_distance_box(
                        "Team 1",
                        team_1_distance,
                        team_colors.get(1, DEFAULT_TEAM_COLORS[1]),
                    ),
                    build_team_distance_box(
                        "Team 2",
                        team_2_distance,
                        team_colors.get(2, DEFAULT_TEAM_COLORS[2]),
                    ),
                    col_widths=(6, 6),
                ),
                ui.p(
                    "Suma dystansów zawodników (zaokrąglona, w metrach)",
                    class_="text-muted small mt-2",
                    style="text-align: center;",
                ),
            )
        except Exception as exc:
            return ui.p(
                f"Nie udało się wczytać danych trackingu: {exc}",
                style="color: #dc3545;",
            )
