import pandas as pd
import os
from shiny import render, reactive, ui


# draws a horizontal comparison bar for a single stat (home vs away)
def draw_stat_bar(stat_name, home_val, away_val):
    # extract numeric value from string, stripping % signs and parentheses
    def extract_num(val):
        if pd.isna(val) or val == "": return 0
        val_str = str(val).replace('%', '').split('(')[0].strip()
        try:
            return float(val_str)
        except ValueError:
            return 0

    h_num = extract_num(home_val)
    a_num = extract_num(away_val)

    # calculate percentage width for each side of the bar
    total = abs(h_num) + abs(a_num)
    h_pct = (abs(h_num) / total * 100) if total > 0 else 50
    a_pct = (abs(a_num) / total * 100) if total > 0 else 50

    return ui.div(
        # row with stat name and values on each side
        ui.div(
            ui.span(str(home_val), style="font-weight: bold; font-size: 1.2em; color: #0d6efd;"),
            ui.span(stat_name, style="font-weight: bold; color: #495057; font-size: 0.9em; text-transform: uppercase;"),
            ui.span(str(away_val), style="font-weight: bold; font-size: 1.2em; color: #dc3545;"),
            style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; margin-top: 15px;"
        ),
        # visual bar split between home (blue) and away (red)
        ui.div(
            ui.div(
                style=f"width: {h_pct}%; background-color: #0d6efd; height: 10px; border-radius: 5px 0 0 5px; transition: width 0.5s;"),
            ui.div(
                style=f"width: {a_pct}%; background-color: #dc3545; height: 10px; border-radius: 0 5px 5px 0; transition: width 0.5s;"),
            style="display: flex; width: 100%; background-color: #e9ecef; border-radius: 5px;"
        )
    )


def server(input, output, session):
    # load csv data on startup or when the reload button is clicked
    @reactive.calc
    @reactive.event(input.btn_reload, ignore_none=False)
    def load_data():
        file_path = "data/output/flashscore_results.csv"
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                return pd.read_csv(file_path)
            except pd.errors.EmptyDataError:
                return pd.DataFrame({"Błąd": ["Plik CSV jest uszkodzony."]})
        return pd.DataFrame({"Błąd": ["Brak pliku CSV."]})

    @render.text
    def match_title():
        df = load_data()
        if "League" in df.columns and "Round" in df.columns: return f"{df['League'].iloc[0]} | {df['Round'].iloc[0]}"
        return "Brak danych"

    @render.text
    def home_team_name():
        df = load_data()
        return f"Gospodarze: {df['Home'].iloc[0]}" if "Home" in df.columns else "Gospodarze"

    @render.text
    def away_team_name():
        df = load_data()
        return f"Goście: {df['Away'].iloc[0]}" if "Away" in df.columns else "Goście"

    @render.text
    def home_team_score():
        df = load_data()
        return f"{int(df['Home_Score'].iloc[0])}" if "Home_Score" in df.columns and pd.notna(
            df['Home_Score'].iloc[0]) else "-"

    @render.text
    def away_team_score():
        df = load_data()
        return f"{int(df['Away_Score'].iloc[0])}" if "Away_Score" in df.columns and pd.notna(
            df['Away_Score'].iloc[0]) else "-"

    @render.text
    def match_date():
        df = load_data()
        return f"{df['Date'].iloc[0]} ({df['Time'].iloc[0]})" if "Date" in df.columns else "-"

    # pre-match betting odds (1 = home win, x = draw, 2 = away win)
    @render.text
    def odd_1():
        df = load_data()
        return f"{df['Best_Odd_1_FT'].iloc[0]}" if "Best_Odd_1_FT" in df.columns and pd.notna(
            df['Best_Odd_1_FT'].iloc[0]) else "-"

    @render.text
    def odd_x():
        df = load_data()
        return f"{df['Best_Odd_X_FT'].iloc[0]}" if "Best_Odd_X_FT" in df.columns and pd.notna(
            df['Best_Odd_X_FT'].iloc[0]) else "-"

    @render.text
    def odd_2():
        df = load_data()
        return f"{df['Best_Odd_2_FT'].iloc[0]}" if "Best_Odd_2_FT" in df.columns and pd.notna(
            df['Best_Odd_2_FT'].iloc[0]) else "-"

    # --- helper function for generating stat bars ---
    def generate_bars_for_group(df, stats_dict):
        if df.empty or "Błąd" in df.columns: return ui.p("Brak danych.", style="color: gray;")

        elements = []
        # these stats are stored as decimals (0-1) and need to be shown as percentages
        percentage_stats = ["Ball possession", "Passes", "Long passes", "Passes in final third", "Crosses", "Tackles"]

        for original_name, pl_name in stats_dict.items():
            home_col = f"Home_{original_name}"
            away_col = f"Away_{original_name}"

            if home_col in df.columns and away_col in df.columns:
                h_val = df[home_col].iloc[0]
                a_val = df[away_col].iloc[0]

                if pd.notna(h_val) and pd.notna(a_val):
                    if original_name in percentage_stats:
                        h_val_display = f"{int(float(h_val) * 100)}%"
                        a_val_display = f"{int(float(a_val) * 100)}%"
                    else:
                        h_val_display = str(int(h_val)) if float(h_val).is_integer() else str(h_val)
                        a_val_display = str(int(a_val)) if float(a_val).is_integer() else str(a_val)

                    elements.append(draw_stat_bar(pl_name, h_val_display, a_val_display))

        return ui.div(*elements) if elements else ui.p("Brak statystyk dla tej kategorii.", style="color: gray;")

    # --- rendering individual stat tabs ---

    @render.ui
    def stats_main():
        return generate_bars_for_group(load_data(), {
            "Ball possession": "Posiadanie piłki",
            "Expected goals (xG)": "Oczekiwane gole (xG)",
            "Total shots": "Strzały ogółem",
            "Shots on target": "Strzały celne",
            "Big chances": "Wielkie szanse",
            "Corner kicks": "Rzuty rożne"
        })

    @render.ui
    def stats_attack():
        return generate_bars_for_group(load_data(), {
            "xG on target (xGOT)": "Oczekiwane gole celne (xGOT)",
            "Shots off target": "Strzały niecelne",
            "Blocked shots": "Zablokowane strzały",
            "Shots inside the box": "Strzały z pola karnego",
            "Shots outside the box": "Strzały z dystansu",
            "Hit the woodwork": "Słupki / Poprzeczki",
            "Headed goals": "Gole głową",
            "Touches in opposition box": "Kontakty w polu karnym rywala",
            "Offsides": "Spalone"
        })

    @render.ui
    def stats_passing():
        return generate_bars_for_group(load_data(), {
            "Passes": "Skuteczność podań",
            "Accurate through passes": "Celne prostopadłe",
            "Long passes": "Skuteczność długich podań",
            "Passes in final third": "Podania w ostatniej tercji",
            "Crosses": "Skuteczność dośrodkowań",
            "Expected assists (xA)": "Oczekiwane asysty (xA)",
            "Free kicks": "Rzuty wolne",
            "Throw ins": "Rzuty z autu"
        })

    @render.ui
    def stats_defense():
        return generate_bars_for_group(load_data(), {
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
            "Red cards": "Czerwone kartki"
        })