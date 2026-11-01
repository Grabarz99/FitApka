import os
import sys
import importlib.util

# Ustaw folder na dane aplikacji
storage_dir = "/tmp/fitapp_data"
os.makedirs(storage_dir, exist_ok=True)
os.environ["FLET_APP_STORAGE_DATA"] = storage_dir

port = int(os.environ.get("PORT", 10000))

import flet as ft

# Blokuj ft.app żeby nie uruchamiał się przy imporcie main.py
original_app = ft.app
ft.app = lambda *args, **kwargs: None

# Importuj main.py bez uruchamiania ft.app
spec = importlib.util.spec_from_file_location("main_module", "main.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Przywróć oryginalne ft.app
ft.app = original_app

# Uruchom aplikację webową
ft.app(
    target=mod.main,
    view=ft.AppView.WEB_BROWSER,
    port=port,
    host="0.0.0.0"
)
