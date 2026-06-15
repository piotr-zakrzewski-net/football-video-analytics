from shiny import ui
from shinywidgets import output_widget

app_ui = ui.page_navbar(
    # --- flashscore stats tab ---
    ui.nav_panel(
        "📊 Statystyki po meczowe",
        ui.layout_sidebar(
            # 1. Sidebar jako pierwszy argument
            ui.sidebar(
                ui.h4("⚙️ Panel Sterowania"),
                ui.input_text(
                    "url_input",
                    "Wklej link z Flashscore:",
                    placeholder="https://www.flashscore.com/match/...",
                ),
                ui.input_action_button(
                    "btn_scrape", "Pobierz dane", class_="btn-success"
                ),
                ui.hr(),
                ui.input_action_button(
                    "btn_reload", "Odśwież dane z pliku", class_="btn-primary"
                ),
                ui.hr(),
                ui.input_select(
                    "match_selector",
                    "Wybierz spotkanie:",
                    choices=["Wczytaj dane..."],
                    selected="Wczytaj dane...",
                    width="100%",
                ),
                width=320,
            ),
            # 2. Treść główna jako kolejne argumenty
            ui.div(
                ui.h2(
                    ui.output_text("match_title"),
                    class_="text-center mb-4",
                    style="color: #2c3e50; font-weight: bold;",
                ),
                ui.layout_columns(
                    ui.value_box(
                        title=ui.div(
                            ui.output_text("home_team_name"),
                            style="font-size: 1.1em; width: 100%; text-align: center;",
                        ),
                        value=ui.div(
                            "Gole: ",
                            ui.output_text("home_team_score", inline=True),
                            style="width: 100%; text-align: center;",
                        ),
                        theme="bg-primary",
                        showcase=ui.h1("🏠"),
                    ),
                    ui.value_box(
                        title=ui.div(
                            ui.output_text("away_team_name"),
                            style="font-size: 1.1em; width: 100%; text-align: center;",
                        ),
                        value=ui.div(
                            "Gole: ",
                            ui.output_text("away_team_score", inline=True),
                            style="width: 100%; text-align: center;",
                        ),
                        theme="bg-danger",
                        showcase=ui.h1("✈️"),
                    ),
                    ui.value_box(
                        title=ui.div(
                            "Data Spotkania",
                            style="font-size: 1.1em; width: 100%; text-align: center;",
                        ),
                        value=ui.div(
                            ui.output_text("match_date"),
                            style="width: 100%; text-align: center;",
                        ),
                        theme="bg-success",
                        showcase=ui.h1("📅"),
                    ),
                    col_widths=[4, 4, 4],
                ),
                ui.hr(),
                ui.h4(
                    "💰 Kursy Bukmacherskie (Pre-match)",
                    class_="mb-3",
                    style="color: #495057;",
                ),
                ui.layout_columns(
                    ui.value_box(
                        title=ui.div(
                            "Wygrają Gospodarze (1)",
                            style="width: 100%; text-align: center;",
                        ),
                        value=ui.div(
                            ui.output_text("odd_1"),
                            style="width: 100%; text-align: center;",
                        ),
                        theme="bg-light",
                    ),
                    ui.value_box(
                        title=ui.div(
                            "Remis (X)",
                            style="width: 100%; text-align: center;",
                        ),
                        value=ui.div(
                            ui.output_text("odd_x"),
                            style="width: 100%; text-align: center;",
                        ),
                        theme="bg-light",
                    ),
                    ui.value_box(
                        title=ui.div(
                            "Wygrają Goście (2)",
                            style="width: 100%; text-align: center;",
                        ),
                        value=ui.div(
                            ui.output_text("odd_2"),
                            style="width: 100%; text-align: center;",
                        ),
                        theme="bg-light",
                    ),
                    col_widths=[4, 4, 4],
                ),
                ui.br(),
                ui.layout_columns(
                    ui.card(
                        ui.card_header("🕸️ Porównanie Potencjału (Radar)"),
                        ui.output_ui("radar_chart"),
                        full_screen=True,
                    ),
                    ui.card(
                        ui.navset_pill(
                            ui.nav_panel("⭐ Główne", ui.output_ui("stats_main")),
                            ui.nav_panel("⚔️ Atak", ui.output_ui("stats_attack")),
                            ui.nav_panel("👟 Podania", ui.output_ui("stats_passing")),
                            ui.nav_panel(
                                "🛡️ Obrona i Faule", ui.output_ui("stats_defense")
                            ),
                        )
                    ),
                    col_widths=[5, 7],
                ),
            ),
        ),
    ),
    # --- ai video analysis tab ---
    ui.nav_panel(
        "🤖 Analiza AI (Wideo)",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_select("video_selector", "Wybierz nagranie:", choices=[]),
                width=320,
            ),
            ui.layout_columns(
                ui.card(
                    ui.card_header("Zintegrowany Odtwarzacz AI"),
                    ui.output_ui("dynamic_video_player"),
                    full_screen=True,
                ),
                ui.card(
                    ui.card_header("📊 Statystyki Dystansu"),
                    ui.output_ui("distance_stats"),
                ),
                col_widths=(8, 4),
            ),
        ),
    ),
    title="Football Video Analytics",
)
