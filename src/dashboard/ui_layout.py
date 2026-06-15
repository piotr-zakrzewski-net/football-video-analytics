from shiny import ui

# main app layout using a top navigation bar
app_ui = ui.page_navbar(

    # --- flashscore stats tab ---
    ui.nav_panel("📊 Statystyki Flashscore",
                 ui.layout_sidebar(
                     # sidebar with reload button
                     ui.sidebar(
                         ui.h4("⚙️ Panel Sterowania"),
                         ui.input_action_button("btn_reload", "Odśwież dane z pliku", class_="btn-primary"),
                         ui.hr(),
                         ui.p("Kliknij przycisk, aby wczytać najnowszy plik CSV wygenerowany przez bota Flashscore.",
                              style="font-size: 0.9em; color: gray;")
                     ),

                     ui.div(
                         # match title
                         ui.h2(ui.output_text("match_title"), class_="text-center mb-4",
                               style="color: #2c3e50; font-weight: bold;"),

                         # score boxes for home team, away team and date
                         ui.layout_columns(
                             ui.value_box(
                                 title=ui.output_text("home_team_name"),
                                 value=ui.output_text("home_team_score"),
                                 theme="bg-primary",
                                 showcase=ui.h1("🏠")
                             ),
                             ui.value_box(
                                 title=ui.output_text("away_team_name"),
                                 value=ui.output_text("away_team_score"),
                                 theme="bg-danger",
                                 showcase=ui.h1("✈️")
                             ),
                             ui.value_box(
                                 title="Data Spotkania",
                                 value=ui.output_text("match_date"),
                                 theme="bg-success",
                                 showcase=ui.h1("📅")
                             ),
                             col_widths=[4, 4, 4]
                         ),

                         ui.hr(),

                         # pre-match betting odds
                         ui.h4("💰 Kursy Bukmacherskie (Pre-match)", class_="mb-3", style="color: #495057;"),
                         ui.layout_columns(
                             ui.value_box("Wygrają Gospodarze (1)", ui.output_text("odd_1"), theme="bg-light"),
                             ui.value_box("Remis (X)", ui.output_text("odd_x"), theme="bg-light"),
                             ui.value_box("Wygrają Goście (2)", ui.output_text("odd_2"), theme="bg-light"),
                             col_widths=[4, 4, 4]
                         ),

                         ui.br(),

                         # tabbed stats card: main, attack, passing, defense
                         ui.card(
                             ui.navset_pill(
                                 ui.nav_panel("⭐ Główne", ui.output_ui("stats_main")),
                                 ui.nav_panel("⚔️ Atak", ui.output_ui("stats_attack")),
                                 ui.nav_panel("👟 Podania", ui.output_ui("stats_passing")),
                                 ui.nav_panel("🛡️ Obrona i Faule", ui.output_ui("stats_defense"))
                             )
                         )
                     )
                 )
                 ),

    # --- ai video analysis tab (work in progress) ---
    ui.nav_panel("🤖 Analiza AI (Wideo)",
                 ui.card(
                     ui.card_header("Silnik Wizyjny (YOLOv8 & ByteTrack)"),
                     ui.h5("Moduł w fazie rozwoju 🚧"),
                     ui.p(
                         "W tym miejscu w przyszłości pojawi się zintegrowany odtwarzacz wideo z naniesionymi bounding boxami na zawodników oraz tabela dystansów.")
                 )
                 ),

    title="Football Video Analytics"
)