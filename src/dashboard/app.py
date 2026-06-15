from shiny import App
from ui_layout import app_ui
from server_logic import server

# combine ui and server into a single app
app = App(app_ui, server)