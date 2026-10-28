import os
import flet as ft
from datetime import datetime, date
from database import FitDatabase
from ai_service import AIService


def main(page: ft.Page):
    page.title = "Fit AI App"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.bgcolor = "#0A0A0F"

    storage_dir = os.getenv("FLET_APP_STORAGE_DATA", os.path.expanduser("~"))
    os.makedirs(storage_dir, exist_ok=True)
    db_path = os.path.join(storage_dir, "fit_app.db")

    db = FitDatabase(db_path=db_path)
    ai = AIService(db)

    today_str = datetime.now().strftime("%Y-%m-%d")
    current_date = ft.Ref[str]()
    current_date_value = [today_str]

    # =========================================================================
    # HELPERS UI
    # =========================================================================
    def show_msg(text, is_error=False):
        snack = ft.SnackBar(
            content=ft.Text(text, color="white", weight=ft.FontWeight.W_500),
            bgcolor="#C62828" if is_error else "#2E7D32",
            duration=3000
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def make_header(title, subtitle=None):
        children = [ft.Text(title, size=22, weight=ft.FontWeight.BOLD, color="white")]
        if subtitle:
            children.append(ft.Text(subtitle, size=13, color="#9E9E9E"))
        return ft.Container(
            padding=ft.padding.only(left=16, right=16, top=16, bottom=8),
            content=ft.Column(children, spacing=2)
        )

    def make_card(content, padding=14):
        return ft.Container(
            margin=ft.margin.symmetric(horizontal=12, vertical=5),
            padding=padding,
            bgcolor="#16161E",
            border_radius=16,
            border=ft.border.all(1, "#2A2A35"),
            content=content
        )

    def accent_btn(text, icon, on_click, color="#00C853"):
        return ft.ElevatedButton(
            text,
            icon=icon,
            bgcolor=color,
            color="white",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                elevation=0,
            ),
            on_click=on_click
        )

    loading_bar = ft.ProgressBar(visible=False, color="#00E676", bgcolor="#1A1A24", height=3)

    # =========================================================================
    # ZAKŁADKA 1: DIETA I KALORIE
    # =========================================================================
    diet_summary_text = ft.Text(size=13, color="#BDBDBD")
    kcal_main_text = ft.Text("0 / 2200 kcal", size=28, weight=ft.FontWeight.BOLD, color="white")
    kcal_progress = ft.ProgressBar(value=0, color="#00E676", bgcolor="#2A2A35", height=8, border_radius=4)

    macro_p_bar = ft.ProgressBar(value=0, color="#42A5F5", bgcolor="#2A2A35", height=6, border_radius=3)
    macro_f_bar = ft.ProgressBar(value=0, color="#FFA726", bgcolor="#2A2A35", height=6, border_radius=3)
    macro_c_bar = ft.ProgressBar(value=0, color="#AB47BC", bgcolor="#2A2A35", height=6, border_radius=3)
    macro_p_txt = ft.Text("B: 0/160g", size=12, color="#42A5F5")
    macro_f_txt = ft.Text("T: 0/70g", size=12, color="#FFA726")
    macro_c_txt = ft.Text("W: 0/230g", size=12, color="#AB47BC")

    meals_column = ft.Column(spacing=8)

    meal_type_dd = ft.Dropdown(
        label="Posiłek",
        value="Śniadanie",
        options=[
            ft.dropdown.Option("Śniadanie"),
            ft.dropdown.Option("II Śniadanie"),
            ft.dropdown.Option("Obiad"),
            ft.dropdown.Option("Kolacja"),
        ],
        expand=True,
        bgcolor="#1E1E2A",
        border_color="#3A3A4A",
        focused_border_color="#00E676",
    )
    food_input = ft.TextField(
        label="Co zjadłeś? (np. 200g kurczaka i 100g ryżu)",
        multiline=True,
        min_lines=1,
        max_lines=3,
        bgcolor="#1E1E2A",
        border_color="#3A3A4A",
        focused_border_color="#00E676",
        border_radius=12,
    )
    barcode_input = ft.TextField(
        label="Kod kreskowy",
        expand=2,
        bgcolor="#1E1E2A",
        border_color="#3A3A4A",
        focused_border_color="#00E676",
        border_radius=12,
    )
    barcode_weight = ft.TextField(
        label="Waga (g)",
        value="100",
        width=90,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A",
        border_color="#3A3A4A",
        focused_border_color="#00E676",
        border_radius=12,
    )

    selected_image_path = {"path": None}
    image_status_txt = ft.Text("Brak zdjęcia", size=12, italic=True, color="#666666")

    def on_photo_picked(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            selected_image_path["path"] = e.files[0].path
            image_status_txt.value = f"✓ {e.files[0].name}"
            image_status_txt.color = "#00E676"
        else:
            selected_image_path["path"] = None
            image_status_txt.value = "Brak zdjęcia"
            image_status_txt.color = "#666666"
        page.update()

    file_picker = ft.FilePicker(on_result=on_photo_picked)
    page.overlay.append(file_picker)

    # Kalendarz - DatePicker
    def on_date_picked(e):
        if e.value:
            picked = e.value
            if isinstance(picked, datetime):
                current_date_value[0] = picked.strftime("%Y-%m-%d")
            else:
                current_date_value[0] = str(picked)[:10]
            date_display_btn.text = current_date_value[0]
            refresh_diet()
        page.update()

    date_picker = ft.DatePicker(
        on_change=on_date_picked,
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2030, 12, 31),
    )
    page.overlay.append(date_picker)

    def open_date_picker(e):
        try:
            y, m, d2 = current_date_value[0].split("-")
            date_picker.value = datetime(int(y), int(m), int(d2))
        except Exception:
            date_picker.value = datetime.now()
        date_picker.open = True
        page.update()

    date_display_btn = ft.ElevatedButton(
        today_str,
        icon="calendar_today",
        on_click=open_date_picker,
        bgcolor="#1E1E2A",
        color="white",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            side=ft.BorderSide(1, "#3A3A4A"),
            elevation=0,
        ),
    )

    def refresh_diet():
        date_val = current_date_value[0]
        meals = db.get_meals_by_date(date_val)

        total_kcal = sum(m[3] for m in meals)
        total_p = round(sum(m[4] for m in meals), 1)
        total_f = round(sum(m[5] for m in meals), 1)
        total_c = round(sum(m[6] for m in meals), 1)

        target_kcal = int(db.get_setting("target_kcal", "2200") or 2200)
        target_p = float(db.get_setting("target_protein", "160") or 160)
        target_f = float(db.get_setting("target_fat", "70") or 70)
        target_c = float(db.get_setting("target_carbs", "230") or 230)

        kcal_main_text.value = f"{total_kcal} / {target_kcal} kcal"
        kcal_progress.value = min(total_kcal / max(target_kcal, 1), 1.0)

        macro_p_txt.value = f"Białko: {total_p}/{target_p}g"
        macro_f_txt.value = f"Tłuszcz: {total_f}/{target_f}g"
        macro_c_txt.value = f"Węgle: {total_c}/{target_c}g"
        macro_p_bar.value = min(total_p / max(target_p, 1), 1.0)
        macro_f_bar.value = min(total_f / max(target_f, 1), 1.0)
        macro_c_bar.value = min(total_c / max(target_c, 1), 1.0)

        remain = target_kcal - total_kcal
        diet_summary_text.value = f"Pozostało: {remain} kcal"

        meals_column.controls.clear()
        for m_type in ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja"]:
            type_meals = [m for m in meals if m[1] == m_type]
            sub_kcal = sum(m[3] for m in type_meals)

            items_ui = []
            for m in type_meals:
                m_id, _, m_name, m_kcal, m_p, m_f, m_c = m
                items_ui.append(
                    ft.Container(
                        padding=ft.padding.symmetric(vertical=6, horizontal=4),
                        content=ft.Row([
                            ft.Column([
                                ft.Text(m_name, weight=ft.FontWeight.W_500, size=14),
                                ft.Row([
                                    ft.Container(
                                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        bgcolor="#1A2A1A",
                                        border_radius=6,
                                        content=ft.Text(f"{m_kcal} kcal", size=11, color="#00E676")
                                    ),
                                    ft.Container(
                                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        bgcolor="#1A1A2A",
                                        border_radius=6,
                                        content=ft.Text(f"B:{m_p}g", size=11, color="#42A5F5")
                                    ),
                                    ft.Container(
                                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        bgcolor="#2A1A0A",
                                        border_radius=6,
                                        content=ft.Text(f"T:{m_f}g", size=11, color="#FFA726")
                                    ),
                                    ft.Container(
                                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        bgcolor="#1E1A2A",
                                        border_radius=6,
                                        content=ft.Text(f"W:{m_c}g", size=11, color="#AB47BC")
                                    ),
                                ], spacing=4, wrap=True)
                            ], expand=True, spacing=4),
                            ft.IconButton(
                                icon="delete_outline",
                                icon_color="#EF5350",
                                icon_size=20,
                                on_click=lambda e, mid=m_id: delete_meal_click(mid)
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    )
                )

            if not items_ui:
                items_ui.append(
                    ft.Container(
                        padding=ft.padding.symmetric(vertical=8),
                        content=ft.Text("Brak wpisów", size=12, color="#444444", italic=True)
                    )
                )

            meals_column.controls.append(
                make_card(
                    ft.Column([
                        ft.Row([
                            ft.Text(m_type, size=15, weight=ft.FontWeight.BOLD, color="#00E676"),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                bgcolor="#1A2A1A",
                                border_radius=8,
                                content=ft.Text(f"{sub_kcal} kcal", size=13, weight=ft.FontWeight.BOLD, color="#00E676")
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(height=1, color="#2A2A35"),
                        *items_ui
                    ])
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
                current_date_value[0],
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
            image_status_txt.color = "#666666"
            refresh_diet()
            show_msg("✓ Dodano posiłek wyliczony przez AI!")
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
                current_date_value[0],
                meal_type_dd.value,
                res["name"],
                res["kcal"],
                res["protein"],
                res["fat"],
                res["carbs"]
            )
            barcode_input.value = ""
            refresh_diet()
            show_msg(f"✓ Dodano: {res['name']}")
        except Exception as ex:
            show_msg(str(ex), True)
        finally:
            loading_bar.visible = False
            page.update()

    diet_view = ft.Column([
        ft.Container(
            padding=ft.padding.only(left=16, right=16, top=16, bottom=8),
            content=ft.Row([
                ft.Text("Dziennik Kalorii", size=22, weight=ft.FontWeight.BOLD, color="white", expand=True),
                date_display_btn,
                ft.IconButton(icon="refresh", icon_color="#00E676", on_click=lambda _: refresh_diet()),
            ])
        ),
        # Karta podsumowania kalorii
        make_card(
            ft.Column([
                ft.Row([
                    ft.Column([
                        kcal_main_text,
                        diet_summary_text,
                    ], expand=True),
                    ft.Container(
                        width=60, height=60,
                        bgcolor="#1A2A1A",
                        border_radius=30,
                        content=ft.Icon("local_fire_department", color="#00E676", size=30),
                        alignment=ft.alignment.center,
                    )
                ]),
                ft.Container(height=8),
                kcal_progress,
                ft.Container(height=12),
                ft.Row([
                    ft.Column([macro_p_txt, macro_p_bar], expand=True),
                ]),
                ft.Container(height=6),
                ft.Row([
                    ft.Column([macro_f_txt, macro_f_bar], expand=True),
                ]),
                ft.Container(height=6),
                ft.Row([
                    ft.Column([macro_c_txt, macro_c_bar], expand=True),
                ]),
            ])
        ),
        # Karta dodawania posiłku
        make_card(
            ft.Column([
                ft.Row([
                    ft.Icon("add_circle_outline", color="#00E676", size=20),
                    ft.Text("Dodaj posiłek", weight=ft.FontWeight.BOLD, size=15),
                ], spacing=8),
                ft.Container(height=4),
                meal_type_dd,
                food_input,
                ft.Row([
                    ft.ElevatedButton(
                        "Zdjęcie",
                        icon="camera_alt",
                        bgcolor="#1E1E2A",
                        color="white",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            side=ft.BorderSide(1, "#3A3A4A"),
                            elevation=0,
                        ),
                        on_click=lambda _: file_picker.pick_files(
                            allow_multiple=False,
                            file_type=ft.FilePickerFileType.IMAGE
                        )
                    ),
                    image_status_txt,
                ], spacing=10),
                accent_btn("Policz przez AI i dodaj", "auto_awesome", add_food_ai_click),
                ft.Divider(color="#2A2A35"),
                ft.Row([
                    barcode_input,
                    barcode_weight,
                    ft.IconButton(
                        icon="qr_code_scanner",
                        bgcolor="#1565C0",
                        icon_color="white",
                        on_click=add_barcode_click
                    )
                ])
            ])
        ),
        meals_column
    ], visible=True)

    # =========================================================================
    # ZAKŁADKA 2: PRZEPISY + LISTA ZAKUPÓW
    # =========================================================================
    recipe_query = ft.TextField(
        label="Czego szukasz? (np. obiad z kurczakiem do 600 kcal, min 45g białka)",
        multiline=True,
        bgcolor="#1E1E2A",
        border_color="#3A3A4A",
        focused_border_color="#1E88E5",
        border_radius=12,
    )
    recipes_list_col = ft.Column(spacing=8)
    shopping_list_col = ft.Column(spacing=4)
    manual_shop_item = ft.TextField(
        label="Dodaj produkt ręcznie",
        expand=True,
        bgcolor="#1E1E2A",
        border_color="#3A3A4A",
        focused_border_color="#00E676",
        border_radius=12,
    )

    def refresh_recipes_and_shopping():
        recipes_list_col.controls.clear()
        for r in db.get_recipes():
            ing_text = ", ".join(r["ingredients"])
            recipes_list_col.controls.append(
                make_card(
                    ft.Column([
                        ft.Text(r["title"], size=16, weight=ft.FontWeight.BOLD, color="#00E676"),
                        ft.Row([
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                bgcolor="#1A2A1A", border_radius=6,
                                content=ft.Text(f"{r['kcal']} kcal", size=11, color="#00E676")
                            ),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                bgcolor="#1A1A2A", border_radius=6,
                                content=ft.Text(f"B:{r['protein']}g", size=11, color="#42A5F5")
                            ),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                bgcolor="#2A1A0A", border_radius=6,
                                content=ft.Text(f"T:{r['fat']}g", size=11, color="#FFA726")
                            ),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                bgcolor="#1E1A2A", border_radius=6,
                                content=ft.Text(f"W:{r['carbs']}g", size=11, color="#AB47BC")
                            ),
                        ], spacing=4, wrap=True),
                        ft.Text(f"Składniki: {ing_text}", size=12, color="#BDBDBD"),
                        ft.Text(r["instructions"], size=12, color="#757575"),
                        ft.Row([
                            ft.ElevatedButton(
                                "Do zakupów",
                                icon="add_shopping_cart",
                                bgcolor="#1E1E2A",
                                color="white",
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                    side=ft.BorderSide(1, "#3A3A4A"),
                                    elevation=0,
                                ),
                                on_click=lambda e, ings=r["ingredients"]: add_ings_to_shop(ings)
                            ),
                            ft.ElevatedButton(
                                "Zjedz teraz",
                                icon="restaurant",
                                bgcolor="#1565C0",
                                color="white",
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                    elevation=0,
                                ),
                                on_click=lambda e, rec=r: eat_recipe_now(rec)
                            )
                        ], wrap=True, spacing=8)
                    ], spacing=6)
                )
            )

        shopping_list_col.controls.clear()
        for s_id, item_name, is_checked in db.get_shopping_list():
            shopping_list_col.controls.append(
                ft.Checkbox(
                    label=item_name,
                    value=bool(is_checked),
                    active_color="#00E676",
                    on_change=lambda e, sid=s_id: toggle_shop(sid, e.control.value)
                )
            )
        page.update()

    def add_ings_to_shop(ings):
        db.add_shopping_items(ings)
        refresh_recipes_and_shopping()
        show_msg("✓ Dodano składniki do listy zakupów!")

    def eat_recipe_now(rec):
        db.add_meal(today_str, "Obiad", rec["title"], rec["kcal"], rec["protein"], rec["fat"], rec["carbs"])
        refresh_diet()
        show_msg(f"✓ Dodano {rec['title']} do dzisiejszego obiadu!")

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
            show_msg(f"✓ Pobrano {len(found)} przepisów!")
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
            show_msg("Skopiowano! Otwieram Google Keep.")
        else:
            show_msg("Skopiowano listę! Wklej w Notatkach.")

    recipes_view = ft.Column([
        make_header("Przepisy AI i Zakupy"),
        make_card(
            ft.Column([
                ft.Row([
                    ft.Icon("shopping_cart", color="#00E676", size=20),
                    ft.Text("Lista Zakupów", size=15, weight=ft.FontWeight.BOLD),
                ], spacing=8),
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
                    ft.ElevatedButton(
                        "Google Keep",
                        icon="note_add",
                        bgcolor="#1E1E2A",
                        color="white",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            side=ft.BorderSide(1, "#3A3A4A"),
                            elevation=0,
                        ),
                        on_click=lambda _: export_shopping_list("keep")
                    ),
                    ft.ElevatedButton(
                        "Kopiuj",
                        icon="content_copy",
                        bgcolor="#1E1E2A",
                        color="white",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            side=ft.BorderSide(1, "#3A3A4A"),
                            elevation=0,
                        ),
                        on_click=lambda _: export_shopping_list("ios")
                    ),
                    ft.TextButton(
                        "Wyczyść",
                        style=ft.ButtonStyle(color="#EF5350"),
                        on_click=lambda _: (db.clear_shopping_list(), refresh_recipes_and_shopping())
                    )
                ], wrap=True, spacing=8)
            ])
        ),
        make_card(
            ft.Column([
                ft.Row([
                    ft.Icon("search", color="#1E88E5", size=20),
                    ft.Text("Wyszukiwarka przepisów AI", weight=ft.FontWeight.BOLD, size=15),
                ], spacing=8),
                recipe_query,
                accent_btn("Szukaj przepisów pod makro", "auto_awesome", search_recipes_click, "#1565C0"),
            ])
        ),
        recipes_list_col
    ], visible=False)

    # =========================================================================
    # ZAKŁADKA 3: TRENINGI
    # =========================================================================
    act_type_dd = ft.Dropdown(
        label="Rodzaj aktywności",
        value="Siłownia",
        options=[
            ft.dropdown.Option("Siłownia"),
            ft.dropdown.Option("Inna aktywność (Hokej / Kardio / Inne)")
        ],
        bgcolor="#1E1E2A",
        border_color="#3A3A4A",
        focused_border_color="#00E676",
    )
    ex_name = ft.TextField(
        label="Ćwiczenie / Aktywność",
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )
    ex_sets = ft.TextField(label="Serie", value="4", width=80, keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)
    ex_reps = ft.TextField(label="Powt.", value="8", width=80, keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)
    ex_weight = ft.TextField(label="Ciężar (kg)", value="80", width=100, keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)
    ex_duration = ft.TextField(label="Czas (min)", value="60", width=100, keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)
    ex_kcal = ft.TextField(label="Spalone kcal", value="400", width=110, keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)

    workouts_col = ft.Column(spacing=8)
    ai_goal_input = ft.TextField(
        label="Cel dla Trenera AI (np. 4 dni siłowni + hokej, progresja w przysiadzie)",
        multiline=True,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#1E88E5", border_radius=12,
    )
    ai_plans_col = ft.Column(spacing=10)

    def refresh_workouts():
        workouts_col.controls.clear()
        for w in db.get_workouts_by_date(current_date_value[0]):
            w_id, w_type, w_name, w_sets, w_reps, w_kg, w_dur, w_kcal, _ = w
            details = f"{w_sets} serie x {w_reps} powt. | {w_kg} kg" if w_type == "Siłownia" else f"Czas: {w_dur} min | Spalone: {w_kcal} kcal"
            icon = "fitness_center" if w_type == "Siłownia" else "directions_run"
            workouts_col.controls.append(
                make_card(
                    ft.Row([
                        ft.Container(
                            width=40, height=40,
                            bgcolor="#1A2A1A",
                            border_radius=20,
                            content=ft.Icon(icon, color="#00E676", size=20),
                            alignment=ft.alignment.center,
                        ),
                        ft.Column([
                            ft.Text(w_name, weight=ft.FontWeight.BOLD, size=14),
                            ft.Text(details, size=12, color="#9E9E9E"),
                        ], expand=True, spacing=2),
                    ], spacing=12)
                )
            )

        ai_plans_col.controls.clear()
        for p_id, created, p_name, p_text in db.get_ai_plans():
            ai_plans_col.controls.append(
                make_card(
                    ft.Column([
                        ft.Text(f"{p_name}", weight=ft.FontWeight.BOLD, color="#42A5F5", size=15),
                        ft.Text(created, size=11, color="#666666"),
                        ft.Markdown(p_text, selectable=True)
                    ])
                )
            )
        page.update()

    def add_workout_click(e):
        if not ex_name.value.strip():
            show_msg("Podaj nazwę ćwiczenia lub aktywności!", True)
            return
        db.add_workout(
            current_date_value[0],
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
        show_msg("✓ Zapisano trening!")

    def generate_plan_click(e):
        if not ai_goal_input.value.strip():
            show_msg("Opisz swój cel treningowy dla AI!", True)
            return
        loading_bar.visible = True
        page.update()
        try:
            recent = db.get_recent_workouts(limit=30)
            plan_md = ai.generate_workout_plan(ai_goal_input.value.strip(), recent)
            db.save_ai_plan("Plan Treningowy AI", plan_md)
            refresh_workouts()
            show_msg("✓ Trener AI wygenerował nową rozpiskę!")
        except Exception as ex:
            show_msg(str(ex), True)
        finally:
            loading_bar.visible = False
            page.update()

    workout_view = ft.Column([
        make_header("Dziennik Treningowy"),
        make_card(
            ft.Column([
                ft.Row([
                    ft.Icon("add_circle_outline", color="#00E676", size=20),
                    ft.Text("Zapisz serię / aktywność", weight=ft.FontWeight.BOLD, size=15),
                ], spacing=8),
                act_type_dd,
                ex_name,
                ft.Row([ex_sets, ex_reps, ex_weight], wrap=True, spacing=8),
                ft.Row([ex_duration, ex_kcal], wrap=True, spacing=8),
                accent_btn("Dodaj do dziennika", "fitness_center", add_workout_click),
            ])
        ),
        ft.Container(
            padding=ft.padding.only(left=16, top=8, bottom=4),
            content=ft.Text("Dzisiejsze aktywności:", weight=ft.FontWeight.BOLD, color="#9E9E9E", size=13)
        ),
        workouts_col,
        make_card(
            ft.Column([
                ft.Row([
                    ft.Icon("auto_awesome", color="#42A5F5", size=20),
                    ft.Text("Trener AI – Rozpiska i Progresja", weight=ft.FontWeight.BOLD, size=15, color="#42A5F5"),
                ], spacing=8),
                ai_goal_input,
                accent_btn("Generuj plan i progresję ciężaru", "auto_awesome", generate_plan_click, "#1565C0"),
            ])
        ),
        ai_plans_col
    ], visible=False)

    # =========================================================================
    # ZAKŁADKA 4: POSTĘPY I WAGA
    # =========================================================================
    new_weight_input = ft.TextField(
        label="Nowy pomiar wagi (kg)",
        width=180,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )
    weight_status_txt = ft.Text(size=24, weight=ft.FontWeight.BOLD, color="white")
    weight_sub_txt = ft.Text(size=13, color="#9E9E9E")
    weight_history_col = ft.Column(spacing=6)

    def refresh_progress():
        curr_w = float(db.get_setting("current_weight", "90.0") or 90.0)
        targ_w = float(db.get_setting("target_weight", "70.0") or 70.0)
        diff = round(curr_w - targ_w, 1)
        weight_status_txt.value = f"{curr_w} kg"
        weight_sub_txt.value = f"Cel: {targ_w} kg  |  Pozostało: {diff} kg"

        weight_history_col.controls.clear()
        for w_date, w_val in reversed(db.get_weight_logs()):
            weight_history_col.controls.append(
                make_card(
                    ft.Row([
                        ft.Icon("monitor_weight", color="#9E9E9E", size=18),
                        ft.Text(w_date, color="#BDBDBD", size=13),
                        ft.Text(f"{w_val} kg", weight=ft.FontWeight.BOLD, color="#00E676", size=15),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=10
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
            show_msg("✓ Zapisano nowy pomiar wagi!")
        except ValueError:
            show_msg("Wpisz poprawną liczbę!", True)

    progress_view = ft.Column([
        make_header("Twoje Postępy"),
        make_card(
            ft.Column([
                ft.Row([
                    ft.Icon("monitor_weight", color="#00E676", size=24),
                    ft.Column([
                        weight_status_txt,
                        weight_sub_txt,
                    ], spacing=2)
                ], spacing=12),
                ft.Container(height=8),
                ft.Row([
                    new_weight_input,
                    accent_btn("Zapisz", "save", add_weight_click),
                ], spacing=10),
            ])
        ),
        ft.Container(
            padding=ft.padding.only(left=16, top=8, bottom=4),
            content=ft.Text("Historia pomiarów:", weight=ft.FontWeight.BOLD, color="#9E9E9E", size=13)
        ),
        weight_history_col
    ], visible=False)

    # =========================================================================
    # ZAKŁADKA 5: USTAWIENIA + PROFIL OSOBY
    # =========================================================================
    

    # Profil osoby
    profile_name = ft.TextField(
        label="Imię", value=db.get_setting("profile_name", ""),
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )
    profile_age = ft.TextField(
        label="Wiek (lata)", value=db.get_setting("profile_age", "25"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12, width=120,
    )
    profile_height = ft.TextField(
        label="Wzrost (cm)", value=db.get_setting("height", "175"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12, width=120,
    )
    profile_gender = ft.Dropdown(
        label="Płeć",
        value=db.get_setting("profile_gender", "Mężczyzna"),
        options=[
            ft.dropdown.Option("Mężczyzna"),
            ft.dropdown.Option("Kobieta"),
        ],
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", expand=True,
    )
    profile_activity = ft.Dropdown(
        label="Poziom aktywności",
        value=db.get_setting("profile_activity", "Umiarkowanie aktywny"),
        options=[
            ft.dropdown.Option("Siedzący tryb życia"),
            ft.dropdown.Option("Lekko aktywny"),
            ft.dropdown.Option("Umiarkowanie aktywny"),
            ft.dropdown.Option("Bardzo aktywny"),
            ft.dropdown.Option("Ekstremalnie aktywny"),
        ],
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676",
    )

    bmr_result_txt = ft.Text("", size=13, color="#9E9E9E")

    def calc_bmr():
        try:
            age = int(profile_age.value or 25)
            height = float(profile_height.value or 175)
            weight = float(db.get_setting("current_weight", "80") or 80)
            gender = profile_gender.value

            # Mifflin-St Jeor
            if gender == "Mężczyzna":
                bmr = 10 * weight + 6.25 * height - 5 * age + 5
            else:
                bmr = 10 * weight + 6.25 * height - 5 * age - 161

            activity_map = {
                "Siedzący tryb życia": 1.2,
                "Lekko aktywny": 1.375,
                "Umiarkowanie aktywny": 1.55,
                "Bardzo aktywny": 1.725,
                "Ekstremalnie aktywny": 1.9,
            }
            factor = activity_map.get(profile_activity.value, 1.55)
            tdee = round(bmr * factor)
            bmr_result_txt.value = f"BMR: {round(bmr)} kcal/dzień  |  TDEE: {tdee} kcal/dzień"
            return tdee
        except Exception:
            return None

    def auto_fill_macros(e):
        tdee = calc_bmr()
        if tdee:
            # Podział: 30% białko, 25% tłuszcz, 45% węgle
            prot = round(tdee * 0.30 / 4)
            fat = round(tdee * 0.25 / 9)
            carbs = round(tdee * 0.45 / 4)
            t_kcal_field.value = str(tdee)
            t_prot_field.value = str(prot)
            t_fat_field.value = str(fat)
            t_carb_field.value = str(carbs)
            page.update()
            show_msg(f"✓ Wyliczono TDEE: {tdee} kcal – makro uzupełnione!")

    t_kcal_field = ft.TextField(
        label="Cel Kalorii (kcal)", value=db.get_setting("target_kcal", "2200"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )
    t_prot_field = ft.TextField(
        label="Cel Białka (g)", value=db.get_setting("target_protein", "160"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )
    t_fat_field = ft.TextField(
        label="Cel Tłuszczu (g)", value=db.get_setting("target_fat", "70"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )
    t_carb_field = ft.TextField(
        label="Cel Węglowodanów (g)", value=db.get_setting("target_carbs", "230"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )
    t_weight_field = ft.TextField(
        label="Docelowa waga (kg)", value=db.get_setting("target_weight", "70.0"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )

    def save_settings_click(e):
        db.set_setting("api_key", api_key_field.value.strip())
        db.set_setting("model_name", model_field.value.strip())
        db.set_setting("profile_name", profile_name.value.strip())
        db.set_setting("profile_age", profile_age.value.strip())
        db.set_setting("height", profile_height.value.strip())
        db.set_setting("profile_gender", profile_gender.value)
        db.set_setting("profile_activity", profile_activity.value)
        db.set_setting("target_kcal", t_kcal_field.value.strip())
        db.set_setting("target_protein", t_prot_field.value.strip())
        db.set_setting("target_fat", t_fat_field.value.strip())
        db.set_setting("target_carbs", t_carb_field.value.strip())
        db.set_setting("target_weight", t_weight_field.value.strip())
        calc_bmr()
        refresh_diet()
        refresh_progress()
        page.update()
        show_msg("✓ Ustawienia zapisane!")

    settings_view = ft.Column([
        make_header("Ustawienia"),
        # API
        make_card(
            ft.Column([
                ft.Row([
                    ft.Icon("key", color="#00E676", size=20),
                    ft.Text("Konfiguracja AI", weight=ft.FontWeight.BOLD, size=15),
                ], spacing=8),
                api_key_field,
                model_field,
                ft.Text(
                    "Modele: gemini-2.0-flash-exp (zalecany) | gemini-3.8-flash | gemini-1.5-flash",
                    size=11, color="#666666", italic=True
                ),
            ])
        ),
        # Profil
        make_card(
            ft.Column([
                ft.Row([
                    ft.Icon("person", color="#42A5F5", size=20),
                    ft.Text("Profil osoby", weight=ft.FontWeight.BOLD, size=15),
                ], spacing=8),
                profile_name,
                ft.Row([profile_age, profile_height], spacing=10),
                profile_gender,
                profile_activity,
                ft.ElevatedButton(
                    "Wylicz BMR / TDEE automatycznie",
                    icon="calculate",
                    bgcolor="#1565C0",
                    color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), elevation=0),
                    on_click=auto_fill_macros
                ),
                bmr_result_txt,
            ])
        ),
        # Cele
        make_card(
            ft.Column([
                ft.Row([
                    ft.Icon("track_changes", color="#FFA726", size=20),
                    ft.Text("Cele i makroskładniki", weight=ft.FontWeight.BOLD, size=15),
                ], spacing=8),
                t_kcal_field,
                ft.Row([t_prot_field, t_fat_field, t_carb_field], wrap=True, spacing=8),
                t_weight_field,
            ])
        ),
        ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            content=accent_btn("Zapisz ustawienia", "save", save_settings_click),
        ),
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
        bgcolor="#0F0F18",
        indicator_color="#1A2A1A",
        destinations=[
            ft.NavigationBarDestination(icon="restaurant_outlined", selected_icon="restaurant", label="Dieta"),
            ft.NavigationBarDestination(icon="menu_book_outlined", selected_icon="menu_book", label="Przepisy"),
            ft.NavigationBarDestination(icon="fitness_center_outlined", selected_icon="fitness_center", label="Trening"),
            ft.NavigationBarDestination(icon="trending_up", label="Postępy"),
            ft.NavigationBarDestination(icon="settings_outlined", selected_icon="settings", label="Ustawienia"),
        ]
    )

    page.add(loading_bar, *views)
    refresh_diet()


ft.app(target=main)
