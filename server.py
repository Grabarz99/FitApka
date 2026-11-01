import os
import sys

# Ustaw folder na dane aplikacji
storage_dir = "/tmp/fitapp_data"
os.makedirs(storage_dir, exist_ok=True)
os.environ["FLET_APP_STORAGE_DATA"] = storage_dir

port = int(os.environ.get("PORT", 10000))

import flet as ft

# Importuj tylko funkcję main, nie uruchamiaj ft.app z main.py
import importlib.util
spec = importlib.util.spec_from_file_location("main_module", "main.py")
mod = importlib.util.load_module_from_spec(spec)

# Podmień ft.app żeby nie uruchamiał się przy imporcie
original_app = ft.app
ft.app = lambda **kwargs: None  # blokuj auto-start

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
