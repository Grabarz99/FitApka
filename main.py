import os
import flet as ft
from datetime import datetime
from database import FitDatabase
from ai_service import AIService

def main(page: ft.Page):
    page.title = "Fit AI App"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 12
    page.scroll = ft.ScrollMode.ADAPTIVE

    # Bezpieczna ścieżka do bazy danych na Androidzie i iOS
    storage_dir = os.getenv("FLET_APP_STORAGE_DATA", os.path.expanduser("~"))
    os.makedirs(storage_dir, exist_ok=True)
    db_path = os.path.join(storage_dir, "fit_app.db")

    db = FitDatabase(db_path=db_path)
    ai = AIService(db)

    today_str = datetime.now().strftime("%Y-%m-%d")
    selected_date = ft.TextField(
        value=today_str, label="Data (RRRR-MM-DD)", width=160, height=45, text_size=13
    )

    def show_msg(text, is_error=False):
        snack = ft.SnackBar(
            content=ft.Text(text, color="white"),
            bgcolor="#D32F2F" if is_error else "#388E3C"
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # Pasek ładowania podczas zapytań do AI
    loading_bar = ft.ProgressBar(visible=False, color="#00E676")

    # =========================================================================
    # ZAKŁADKA 1: DIETA I KALORIE (4 POSIŁKI)
    # =========================================================================
    diet_summary_text = ft.Text(size=15, weight=ft.FontWeight.BOLD)
    kcal_progress = ft.ProgressBar(value=0, color="#00E676", bgcolor="#333333", height=10)
    meals_column = ft.Column(spacing=10)

    meal_type_dd = ft.Dropdown(
        label="Posiłek",
        value="Śniadanie",
        options=[
            ft.dropdown.Option("Śniadanie"),
            ft.dropdown.Option("II Śniadanie"),
            ft.dropdown.Option("Obiad"),
            ft.dropdown.Option("Kolacja"),
        ],
         expand=True
    )
    food_input = ft.TextField(
        label="Co zjadłeś? (np. 200g kurczaka i 100g ryżu)",
        multiline=True,
        min_lines=1,
        max_lines=3
    )
    barcode_input = ft.TextField(label="Kod kreskowy", expand=2)
    barcode_weight = ft.TextField(label="Waga (g)", value="100", width=90, keyboard_type=ft.KeyboardType.NUMBER)

    # Obsługa wyboru zdjęcia posiłku z aparatu/galerii telefonu
    selected_image_path = {"path": None}
    image_status_txt = ft.Text("Brak zdjęcia", size=12, italic=True)

    def on_photo_picked(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            selected_image_path["path"] = e.files[0].path
            image_status_txt.value = f"Wybrano: {e.files[0].name}"
        else:
            selected_image_path["path"] = None
            image_status_txt.value = "Brak zdjęcia"
        page.update()

    file_picker = ft.FilePicker(on_result=on_photo_picked)
    page.overlay.append(file_picker)

    def refresh_diet():
        date_val = selected_date.value.strip()
        meals = db.get_meals_by_date(date_val)
        
        total_kcal = sum(m[3] for m in meals)
        total_p = round(sum(m[4] for m in meals), 1)
        total_f = round(sum(m[5] for m in meals), 1)
        total_c = round(sum(m[6] for m in meals), 1)

        target_kcal = int(db.get_setting("target_kcal", "2200") or 2200)
        target_p = db.get_setting("target_protein", "160")
        target_f = db.get_setting("target_fat", "70")
        target_c = db.get_setting("target_carbs", "230")

        diet_summary_text.value = (
            f"Kalorie: {total_kcal} / {target_kcal} kcal\n"
            f"B: {total_p}/{target_p}g  |  T: {total_f}/{target_f}g  |  W: {total_c}/{target_c}g"
        )
        kcal_progress.value = min(total_kcal / max(target_kcal, 1), 1.0)

        meals_column.controls.clear()
        for m_type in ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja"]:
            type_meals = [m for m in meals if m[1] == m_type]
            sub_kcal = sum(m[3] for m in type_meals)
            
            items_ui = []
            for m in type_meals:
                m_id, _, m_name, m_kcal, m_p, m_f, m_c = m
                items_ui.append(
                    ft.Row([
                        ft.Column([
                            ft.Text(m_name, weight=ft.FontWeight.W_500),
                            ft.Text(f"{m_kcal} kcal | B:{m_p}g T:{m_f}g W:{m_c}g", size=12, color="#AAAAAA")
                        ], expand=True),
                        ft.IconButton(
                            icon="delete_outline",
                            icon_color="#EF5350",
                            on_click=lambda e, mid=m_id: delete_meal_click(mid)
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )

            if not items_ui:
                items_ui.append(ft.Text("Brak wpisów", size=12, color="#666666", italic=True))

            meals_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=12,
                        content=ft.Column([
                            ft.Row([
                                ft.Text(m_type, size=16, weight=ft.FontWeight.BOLD, color="#00E676"),
                                ft.Text(f"{sub_kcal} kcal", size=14, weight=ft.FontWeight.BOLD)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Divider(height=8),
                            *items_ui
                        ])
                    )
                )
            )
        page.update()

    def delete_meal_click(meal_id):
        db.delete_meal(meal_id)
        refresh_diet()

    def add_food_ai_click(e):
        if not food_input.value.strip() and not selected_image_path["path"]:
            show_msg("Opisz posiłek lub dodaj zdjęcie talerza!", True)
            return
        loading_bar.visible = True
        page.update()
        try:
            res = ai.analyze_food(food_input.value.strip(), selected_image_path["path"])
            db.add_meal(
                selected_date.value.strip(),
                meal_type_dd.value,
                res.get("name", "Posiłek"),
                res.get("kcal", 0),
                res.get("protein", 0),
                res.get("fat", 0),
                res.get("carbs", 0)
            )
            food_input.value = ""
            selected_image_path["path"] = None
            image_status_txt.value = "Brak zdjęcia"
            refresh_diet()
            show_msg("Dodano posiłek wyliczony przez AI!")
        except Exception as ex:
            show_msg(str(ex), True)
        finally:
            loading_bar.visible = False
            page.update()

    def add_barcode_click(e):
        if not barcode_input.value.strip():
            show_msg("Wpisz kod kreskowy produktu!", True)
            return
        loading_bar.visible = True
        page.update()
        try:
            res = ai.get_product_by_barcode(barcode_input.value.strip(), float(barcode_weight.value or 100))
            db.add_meal(
                selected_date.value.strip(),
                meal_type_dd.value,
                res["name"],
                res["kcal"],
                res["protein"],
                res["fat"],
                res["carbs"]
            )
            barcode_input.value = ""
            refresh_diet()
            show_msg(f"Dodano: {res['name']}")
        except Exception as ex:
            show_msg(str(ex), True)
        finally:
            loading_bar.visible = False
            page.update()

    diet_view = ft.Column([
        ft.Row([
            ft.Text("Dziennik Kalorii", size=20, weight=ft.FontWeight.BOLD, expand=True),
            selected_date,
            ft.IconButton(icon="refresh", on_click=lambda _: refresh_diet())
        ]),
        diet_summary_text,
        kcal_progress,
        ft.Card(
            content=ft.Container(
                padding=12,
                content=ft.Column([
                    ft.Text("Dodaj posiłek (AI / Kod kreskowy)", weight=ft.FontWeight.BOLD),
                    meal_type_dd,
                    food_input,
                    ft.Row([
                        ft.ElevatedButton(
                            "Zdjęcie",
                            icon="camera_alt",
                            on_click=lambda _: file_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)
                        ),
                        image_status_txt,
                    ]),
                    ft.ElevatedButton(
                        "Policz przez AI i dodaj",
                        icon="auto_awesome",
                        bgcolor="#00C853",
                        color="white",
                        on_click=add_food_ai_click
                    ),
                    ft.Divider(),
                    ft.Row([
                        barcode_input,
                        barcode_weight,
                        ft.IconButton(icon="qr_code_scanner", bgcolor="#1E88E5", icon_color="white", on_click=add_barcode_click)
                    ])
                ])
            )
        ),
        meals_column
    ], visible=True)

    # =========================================================================
    # ZAKŁADKA 2: PRZEPISY Z INTERNETU (AI) + LISTA ZAKUPÓW
    # =========================================================================
    recipe_query = ft.TextField(
        label="Czego szukasz? (np. obiad z kurczakiem do 600 kcal, min 45g białka)",
        multiline=True
    )
    recipes_list_col = ft.Column(spacing=10)
    shopping_list_col = ft.Column(spacing=4)
    manual_shop_item = ft.TextField(label="Dodaj produkt ręcznie", expand=True)

    def refresh_recipes_and_shopping():
        # Przepisy
        recipes_list_col.controls.clear()
        for r in db.get_recipes():
            ing_text = ", ".join(r["ingredients"])
            recipes_list_col.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=12,
                        content=ft.Column([
                            ft.Text(r["title"], size=16, weight=ft.FontWeight.BOLD, color="#00E676"),
                            ft.Text(f"{r['kcal']} kcal | B: {r['protein']}g | T: {r['fat']}g | W: {r['carbs']}g", size=12, color="#BDBDBD"),
                            ft.Text(f"Składniki: {ing_text}", size=13),
                            ft.Text(r["instructions"], size=12, color="#9E9E9E"),
                            ft.Row([
                                ft.ElevatedButton(
                                    "Składniki do zakupów",
                                    icon="add_shopping_cart",
                                    on_click=lambda e, ings=r["ingredients"]: add_ings_to_shop(ings)
                                ),
                                ft.ElevatedButton(
                                    "Zjedz teraz (Obiad)",
                                    icon="restaurant",
                                    on_click=lambda e, rec=r: eat_recipe_now(rec)
                                )
                            ], wrap=True)
                        ])
                    )
                )
            )

        # Lista zakupów
        shopping_list_col.controls.clear()
        for s_id, item_name, is_checked in db.get_shopping_list():
            shopping_list_col.controls.append(
                ft.Checkbox(
                    label=item_name,
                    value=bool(is_checked),
                    on_change=lambda e, sid=s_id: toggle_shop(sid, e.control.value)
                )
            )
        page.update()

    def add_ings_to_shop(ings):
        db.add_shopping_items(ings)
        refresh_recipes_and_shopping()
        show_msg("Dodano składniki do listy zakupów!")

    def eat_recipe_now(rec):
        db.add_meal(today_str, "Obiad", rec["title"], rec["kcal"], rec["protein"], rec["fat"], rec["carbs"])
        refresh_diet()
        show_msg(f"Dodano {rec['title']} do dzisiejszego obiadu!")

    def toggle_shop(sid, val):
        db.toggle_shopping_item(sid, val)
        refresh_recipes_and_shopping()

    def search_recipes_click(e):
        if not recipe_query.value.strip():
            show_msg("Wpisz kryteria przepisu!", True)
            return
        loading_bar.visible = True
        page.update()
        try:
            found = ai.search_recipes(recipe_query.value.strip())
            for r in found:
                db.save_recipe(
                    r.get("title", "Przepis"),
                    r.get("kcal", 0),
                    r.get("protein", 0),
                    r.get("fat", 0),
                    r.get("carbs", 0),
                    r.get("ingredients", []),
                    r.get("instructions", "")
                )
            refresh_recipes_and_shopping()
            show_msg(f"Pobrano i zapisano {len(found)} przepisy!")
        except Exception as ex:
            show_msg(str(ex), True)
        finally:
            loading_bar.visible = False
            page.update()

    def export_shopping_list(target):
        items = db.get_shopping_list()
        unchecked = [f"☐ {i[1]}" for i in items if not i[2]]
        if not unchecked:
            show_msg("Lista zakupów jest pusta!", True)
            return
        formatted_text = "LISTA ZAKUPÓW:\n" + "\n".join(unchecked)
        page.set_clipboard(formatted_text)
        if target == "keep":
            page.launch_url("https://keep.google.com/")
            show_msg("Skopiowano! Otwieram Google Keep – kliknij 'Wklej'.")
        else:
            show_msg("Skopiowano sformatowaną listę! Wklej ją jednym kliknięciem w Notatkach.")

    recipes_view = ft.Column([
        ft.Text("Przepisy AI i Lista Zakupów", size=20, weight=ft.FontWeight.BOLD),
        ft.Card(
            content=ft.Container(
                padding=12,
                content=ft.Column([
                    ft.Text("Lista Zakupów", size=16, weight=ft.FontWeight.BOLD, color="#00E676"),
                    ft.Row([
                        manual_shop_item,
                        ft.IconButton(
                            icon="add",
                            bgcolor="#00C853",
                            icon_color="white",
                            on_click=lambda _: (
                                db.add_shopping_items([manual_shop_item.value.strip()]) if manual_shop_item.value.strip() else None,
                                setattr(manual_shop_item, "value", ""),
                                refresh_recipes_and_shopping()
                            )
                        )
                    ]),
                    shopping_list_col,
                    ft.Row([
                        ft.ElevatedButton("Wyślij do Google Keep", icon="note_add", on_click=lambda _: export_shopping_list("keep")),
                        ft.ElevatedButton("Kopiuj do Notatek iOS", icon="content_copy", on_click=lambda _: export_shopping_list("ios")),
                        ft.TextButton("Wyczyść", on_click=lambda _: (db.clear_shopping_list(), refresh_recipes_and_shopping()))
                    ], wrap=True)
                ])
            )
        ),
        ft.Card(
            content=ft.Container(
                padding=12,
                content=ft.Column([
                    ft.Text("Wyszukiwarka przepisów AI", weight=ft.FontWeight.BOLD),
                    recipe_query,
                    ft.ElevatedButton("Szukaj przepisów pod makro", icon="search", bgcolor="#1E88E5", color="white", on_click=search_recipes_click)
                ])
            )
        ),
        recipes_list_col
    ], visible=False)

    # =========================================================================
    # ZAKŁADKA 3: TRENINGI (SIŁOWNIA + INNE AKTYWNOŚCI + TRENER AI)
    # =========================================================================
    act_type_dd = ft.Dropdown(
        label="Rodzaj aktywności",
        value="Siłownia",
        options=[
            ft.dropdown.Option("Siłownia"),
            ft.dropdown.Option("Inna aktywność (Hokej / Kardio / Inne)")
        ]
    )
    ex_name = ft.TextField(label="Ćwiczenie / Aktywność (np. Przysiad, Trening na lodzie)")
    ex_sets = ft.TextField(label="Serie", value="4", width=80, keyboard_type=ft.KeyboardType.NUMBER)
    ex_reps = ft.TextField(label="Powt.", value="8", width=80, keyboard_type=ft.KeyboardType.NUMBER)
    ex_weight = ft.TextField(label="Ciężar (kg)", value="80", width=100, keyboard_type=ft.KeyboardType.NUMBER)
    ex_duration = ft.TextField(label="Czas (min)", value="60", width=100, keyboard_type=ft.KeyboardType.NUMBER)
    ex_kcal = ft.TextField(label="Spalone kcal", value="400", width=110, keyboard_type=ft.KeyboardType.NUMBER)

    workouts_col = ft.Column(spacing=8)
    ai_goal_input = ft.TextField(
        label="Cel dla Trenera AI (np. 4 dni siłowni + hokej, progresja w przysiadzie, ławce i martwym)",
        multiline=True
    )
    ai_plans_col = ft.Column(spacing=10)

    def refresh_workouts():
        workouts_col.controls.clear()
        for w in db.get_workouts_by_date(selected_date.value.strip()):
            w_id, w_type, w_name, w_sets, w_reps, w_kg, w_dur, w_kcal, _ = w
            details = f"{w_sets} serie x {w_reps} powt. | {w_kg} kg" if w_type == "Siłownia" else f"Czas: {w_dur} min | Spalone: {w_kcal} kcal"
            workouts_col.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=10,
                        content=ft.Column([
                            ft.Text(f"[{w_type}] {w_name}", weight=ft.FontWeight.BOLD, color="#00E676"),
                            ft.Text(details, size=13)
                        ])
                    )
                )
            )

        ai_plans_col.controls.clear()
        for p_id, created, p_name, p_text in db.get_ai_plans():
            ai_plans_col.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=12,
                        content=ft.Column([
                            ft.Text(f"{p_name} ({created})", weight=ft.FontWeight.BOLD, color="#42A5F5"),
                            ft.Markdown(p_text)
                        ])
                    )
                )
            )
        page.update()

    def add_workout_click(e):
        if not ex_name.value.strip():
            show_msg("Podaj nazwę ćwiczenia lub aktywności!", True)
            return
        db.add_workout(
            selected_date.value.strip(),
            act_type_dd.value,
            ex_name.value.strip(),
            ex_sets.value or 0,
            ex_reps.value or 0,
            ex_weight.value or 0,
            ex_duration.value or 0,
            ex_kcal.value or 0
        )
        ex_name.value = ""
        refresh_workouts()
        show_msg("Zapisano trening!")

    def generate_plan_click(e):
        if not ai_goal_input.value.strip():
            show_msg("Opisz swój cel treningowy dla AI!", True)
            return
        loading_bar.visible = True
        page.update()
        try:
            recent = db.get_recent_workouts(limit=30)
            plan_md = ai.generate_workout_plan(ai_goal_input.value.strip(), recent)
            db.save_ai_plan("Plan Treningowy i Progresja AI", plan_md)
            refresh_workouts()
            show_msg("Trener AI wygenerował nową rozpiskę!")
        except Exception as ex:
            show_msg(str(ex), True)
        finally:
            loading_bar.visible = False
            page.update()

    workout_view = ft.Column([
        ft.Text("Dziennik Treningowy i Trener AI", size=20, weight=ft.FontWeight.BOLD),
        ft.Card(
            content=ft.Container(
                padding=12,
                content=ft.Column([
                    ft.Text("Zapisz wykonaną serię / aktywność", weight=ft.FontWeight.BOLD),
                    act_type_dd,
                    ex_name,
                    ft.Row([ex_sets, ex_reps, ex_weight], wrap=True),
                    ft.Row([ex_duration, ex_kcal], wrap=True),
                    ft.ElevatedButton("Dodaj do dziennika", icon="fitness_center", bgcolor="#00C853", color="white", on_click=add_workout_click)
                ])
            )
        ),
        ft.Text("Dzisiejsze aktywności:", weight=ft.FontWeight.BOLD),
        workouts_col,
        ft.Divider(),
        ft.Card(
            content=ft.Container(
                padding=12,
                content=ft.Column([
                    ft.Text("Rozpiska i Progresja z AI", size=16, weight=ft.FontWeight.BOLD, color="#42A5F5"),
                    ai_goal_input,
                    ft.ElevatedButton("Generuj plan i progresję ciężaru", icon="auto_awesome", bgcolor="#1E88E5", color="white", on_click=generate_plan_click)
                ])
            )
        ),
        ai_plans_col
    ], visible=False)

    # =========================================================================
    # ZAKŁADKA 4: POSTĘPY I WAGA
    # =========================================================================
    new_weight_input = ft.TextField(label="Nowy pomiar wagi (kg)", width=180, keyboard_type=ft.KeyboardType.NUMBER)
    weight_status_txt = ft.Text(size=16, weight=ft.FontWeight.BOLD)
    weight_history_col = ft.Column(spacing=6)

    def refresh_progress():
        curr_w = float(db.get_setting("current_weight", "90.0") or 90.0)
        targ_w = float(db.get_setting("target_weight", "70.0") or 70.0)
        diff = round(curr_w - targ_w, 1)
        weight_status_txt.value = f"Aktualna waga: {curr_w} kg  |  Cel: {targ_w} kg  (Pozostało: {diff} kg)"

        weight_history_col.controls.clear()
        for w_date, w_val in reversed(db.get_weight_logs()):
            weight_history_col.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=10,
                        content=ft.Row([
                            ft.Text(w_date, color="#BDBDBD"),
                            ft.Text(f"{w_val} kg", weight=ft.FontWeight.BOLD, color="#00E676")
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    )
                )
            )
        page.update()

    def add_weight_click(e):
        if not new_weight_input.value.strip():
            return
        try:
            w_val = float(new_weight_input.value.replace(",", "."))
            db.add_weight_log(today_str, w_val)
            new_weight_input.value = ""
            refresh_progress()
            show_msg("Zapisano nowy pomiar wagi!")
        except ValueError:
            show_msg("Wpisz poprawną liczbę!", True)

    progress_view = ft.Column([
        ft.Text("Twoje Postępy", size=20, weight=ft.FontWeight.BOLD),
        weight_status_txt,
        ft.Row([
            new_weight_input,
            ft.ElevatedButton("Zapisz wagę", icon="monitor_weight", bgcolor="#00C853", color="white", on_click=add_weight_click)
        ]),
        ft.Divider(),
        ft.Text("Historia pomiarów:", weight=ft.FontWeight.BOLD),
        weight_history_col
    ], visible=False)

    # =========================================================================
    # ZAKŁADKA 5: USTAWIENIA (KLUCZ API, MODEL, CELE)
    # =========================================================================
    api_key_field = ft.TextField(label="Klucz Google Gemini API", password=True, can_reveal_password=True, value=db.get_setting("api_key"))
    model_field = ft.TextField(label="Nazwa modelu Gemini (np. gemini-2.5-flash)", value=db.get_setting("model_name", "gemini-2.5-flash"))
    t_kcal_field = ft.TextField(label="Cel Kalorii (kcal)", value=db.get_setting("target_kcal", "2200"), keyboard_type=ft.KeyboardType.NUMBER)
    t_prot_field = ft.TextField(label="Cel Białka (g)", value=db.get_setting("target_protein", "160"), keyboard_type=ft.KeyboardType.NUMBER)
    t_fat_field = ft.TextField(label="Cel Tłuszczu (g)", value=db.get_setting("target_fat", "70"), keyboard_type=ft.KeyboardType.NUMBER)
    t_carb_field = ft.TextField(label="Cel Węglowodanów (g)", value=db.get_setting("target_carbs", "230"), keyboard_type=ft.KeyboardType.NUMBER)
    t_weight_field = ft.TextField(label="Docelowa waga (kg)", value=db.get_setting("target_weight", "70.0"), keyboard_type=ft.KeyboardType.NUMBER)

    def save_settings_click(e):
        db.set_setting("api_key", api_key_field.value.strip())
        db.set_setting("model_name", model_field.value.strip())
        db.set_setting("target_kcal", t_kcal_field.value.strip())
        db.set_setting("target_protein", t_prot_field.value.strip())
        db.set_setting("target_fat", t_fat_field.value.strip())
        db.set_setting("target_carbs", t_carb_field.value.strip())
        db.set_setting("target_weight", t_weight_field.value.strip())
        refresh_diet()
        refresh_progress()
        show_msg("Ustawienia zostały zapisane w pamięci telefonu!")

    settings_view = ft.Column([
        ft.Text("Ustawienia i Konfiguracja AI", size=20, weight=ft.FontWeight.BOLD),
        api_key_field,
        model_field,
        ft.Divider(),
        ft.Text("Cele sylwetkowe i makroskładniki", weight=ft.FontWeight.BOLD),
        t_kcal_field,
        ft.Row([t_prot_field, t_fat_field, t_carb_field], wrap=True),
        t_weight_field,
        ft.ElevatedButton("Zapisz ustawienia", icon="save", bgcolor="#00C853", color="white", on_click=save_settings_click)
    ], visible=False)

    # =========================================================================
    # NAWIGACJA DOLNA
    # =========================================================================
    views = [diet_view, recipes_view, workout_view, progress_view, settings_view]

    def on_nav_change(e):
        idx = e.control.selected_index
        for i, v in enumerate(views):
            v.visible = (i == idx)
        if idx == 0:
            refresh_diet()
        elif idx == 1:
            refresh_recipes_and_shopping()
        elif idx == 2:
            refresh_workouts()
        elif idx == 3:
            refresh_progress()
        page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_nav_change,
        destinations=[
            ft.NavigationBarDestination(icon="restaurant", label="Dieta"),
            ft.NavigationBarDestination(icon="menu_book", label="Przepisy"),
            ft.NavigationBarDestination(icon="fitness_center", label="Trening"),
            ft.NavigationBarDestination(icon="trending_up", label="Postępy"),
            ft.NavigationBarDestination(icon="settings", label="Ustawienia"),
        ]
    )

    page.add(loading_bar, *views)
    refresh_diet()

ft.app(target=main)
