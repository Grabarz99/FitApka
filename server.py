import os
import flet as ft

# Ustaw folder na dane aplikacji
storage_dir = "/tmp/fitapp_data"
os.makedirs(storage_dir, exist_ok=True)
os.environ["FLET_APP_STORAGE_DATA"] = storage_dir

import main as app_main

port = int(os.environ.get("PORT", 10000))

ft.app(
    target=app_main.main,
    view=ft.AppView.WEB_BROWSER,
    port=port,
    host="0.0.0.0"
)