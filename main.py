import os
import flet as ft
from datetime import datetime, timedelta
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

    def make_header(title):
        return ft.Container(
            padding=ft.padding.only(left=16, right=16, top=16, bottom=8),
            content=ft.Text(title, size=22, weight=ft.FontWeight.BOLD, color="white")
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
            text, icon=icon, bgcolor=color, color="white",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), elevation=0),
            on_click=on_click
        )

    loading_bar = ft.ProgressBar(visible=False, color="#00E676", bgcolor="#1A1A24", height=3)

    # =========================================================================
    # DIALOG WYBORU DATY
    # =========================================================================
    date_input_dlg = ft.TextField(
        label="Data (RRRR-MM-DD)", value=today_str,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12, width=200,
    )

    def confirm_date(e):
        val = date_input_dlg.value.strip()
        try:
            datetime.strptime(val, "%Y-%m-%d")
            current_date_value[0] = val
            date_display_btn.text = val
            date_dlg.open = False
            page.update()
            refresh_diet()
        except ValueError:
            show_msg("Nieprawidlowy format daty! Uzyj RRRR-MM-DD", True)

    def set_today(e):
        current_date_value[0] = today_str
        date_input_dlg.value = today_str
        date_display_btn.text = today_str
        date_dlg.open = False
        page.update()
        refresh_diet()

    date_dlg = ft.AlertDialog(
        title=ft.Text("Wybierz date"),
        content=ft.Column([
            date_input_dlg,
            ft.Text("Format: RRRR-MM-DD (np. 2026-10-27)", size=11, color="#666666"),
        ], tight=True, spacing=8),
        actions=[
            ft.TextButton("Dzis", on_click=set_today),
            ft.TextButton("Anuluj", on_click=lambda e: setattr(date_dlg, 'open', False) or page.update()),
            ft.ElevatedButton("OK", bgcolor="#00C853", color="white", on_click=confirm_date),
        ],
        bgcolor="#16161E",
    )
    page.overlay.append(date_dlg)

    def open_date_dialog(e):
        date_input_dlg.value = current_date_value[0]
        date_dlg.open = True
        page.update()

    date_display_btn = ft.ElevatedButton(
        today_str, icon="calendar_today", on_click=open_date_dialog,
        bgcolor="#1E1E2A", color="white",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            side=ft.BorderSide(1, "#3A3A4A"), elevation=0,
        ),
    )

    # =========================================================================
    # ZAKŁADKA 1: DIETA I KALORIE + WYKRES 7 DNI
    # =========================================================================
    diet_summary_text = ft.Text(size=13, color="#BDBDBD")
    kcal_main_text = ft.Text("0 / 2200 kcal", size=26, weight=ft.FontWeight.BOLD, color="white")
    kcal_progress = ft.ProgressBar(value=0, color="#00E676", bgcolor="#2A2A35", height=8, border_radius=4)

    macro_p_bar = ft.ProgressBar(value=0, color="#42A5F5", bgcolor="#2A2A35", height=6, border_radius=3)
    macro_f_bar = ft.ProgressBar(value=0, color="#FFA726", bgcolor="#2A2A35", height=6, border_radius=3)
    macro_c_bar = ft.ProgressBar(value=0, color="#AB47BC", bgcolor="#2A2A35", height=6, border_radius=3)
    macro_p_txt = ft.Text("Bialko: 0/160g", size=12, color="#42A5F5")
    macro_f_txt = ft.Text("Tluszcz: 0/70g", size=12, color="#FFA726")
    macro_c_txt = ft.Text("Wegle: 0/230g", size=12, color="#AB47BC")

    # Wykres 7 dni
    chart_col = ft.Column(spacing=4)

    def build_week_chart():
        chart_col.controls.clear()
        target_kcal = int(db.get_setting("target_kcal", "2200") or 2200)
        days_data = []
        for i in range(6, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            meals = db.get_meals_by_date(d)
            total = sum(m[3] for m in meals)
            label = (datetime.now() - timedelta(days=i)).strftime("%d.%m")
            days_data.append((label, total, d == current_date_value[0]))

        max_kcal = max((d[1] for d in days_data), default=target_kcal)
        max_val = max(max_kcal, target_kcal, 1)

        bars = []
        for label, kcal, is_today in days_data:
            bar_ratio = min(kcal / max_val, 1.0)
            bar_color = "#00E676" if is_today else ("#EF5350" if kcal > target_kcal else "#42A5F5")
            bars.append(
                ft.Column([
                    ft.Text(str(kcal) if kcal > 0 else "", size=9, color="#9E9E9E",
                            text_align=ft.TextAlign.CENTER),
                    ft.Container(
                        width=32,
                        height=max(4, int(60 * bar_ratio)),
                        bgcolor=bar_color,
                        border_radius=ft.border_radius.only(top_left=4, top_right=4),
                    ),
                    ft.Text(label, size=9, color="#9E9E9E" if not is_today else "#00E676",
                            text_align=ft.TextAlign.CENTER,
                            weight=ft.FontWeight.BOLD if is_today else ft.FontWeight.NORMAL),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)
            )

        chart_col.controls.append(
            ft.Column([
                ft.Row([
                    ft.Icon("bar_chart", color="#42A5F5", size=16),
                    ft.Text("Kalorie - ostatnie 7 dni", size=13, weight=ft.FontWeight.BOLD, color="#42A5F5"),
                ], spacing=6),
                ft.Container(height=4),
                ft.Row(bars, alignment=ft.MainAxisAlignment.SPACE_AROUND,
                       vertical_alignment=ft.CrossAxisAlignment.END),
                ft.Row([
                    ft.Container(width=12, height=3, bgcolor="#EF5350", border_radius=2),
                    ft.Text("powyzej celu", size=10, color="#9E9E9E"),
                    ft.Container(width=12, height=3, bgcolor="#42A5F5", border_radius=2),
                    ft.Text("ponizej celu", size=10, color="#9E9E9E"),
                    ft.Container(width=12, height=3, bgcolor="#00E676", border_radius=2),
                    ft.Text("dzis", size=10, color="#9E9E9E"),
                ], spacing=6, wrap=True),
            ])
        )

    meals_column = ft.Column(spacing=8)

    meal_type_dd = ft.Dropdown(
        label="Posilek", value="Sniadanie",
        options=[
            ft.dropdown.Option("Sniadanie"),
            ft.dropdown.Option("II Sniadanie"),
            ft.dropdown.Option("Obiad"),
            ft.dropdown.Option("Kolacja"),
        ],
        expand=True, bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676",
    )
    food_input = ft.TextField(
        label="Co zjadles? (np. 200g kurczaka i 100g ryzu)",
        multiline=True, min_lines=1, max_lines=3,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )
    barcode_input = ft.TextField(
        label="Kod kreskowy", expand=2,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )
    barcode_weight = ft.TextField(
        label="Waga (g)", value="100", width=90,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )

    selected_image_path = {"path": None}
    image_status_txt = ft.Text("Brak zdjecia", size=12, italic=True, color="#666666")

    def on_photo_picked(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            selected_image_path["path"] = e.files[0].path
            image_status_txt.value = f"OK: {e.files[0].name}"
            image_status_txt.color = "#00E676"
        else:
            selected_image_path["path"] = None
            image_status_txt.value = "Brak zdjecia"
            image_status_txt.color = "#666666"
        page.update()

    file_picker = ft.FilePicker(on_result=on_photo_picked)
    page.overlay.append(file_picker)

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
        macro_p_txt.value = f"Bialko: {total_p}/{target_p}g"
        macro_f_txt.value = f"Tluszcz: {total_f}/{target_f}g"
        macro_c_txt.value = f"Wegle: {total_c}/{target_c}g"
        macro_p_bar.value = min(total_p / max(target_p, 1), 1.0)
        macro_f_bar.value = min(total_f / max(target_f, 1), 1.0)
        macro_c_bar.value = min(total_c / max(target_c, 1), 1.0)
        diet_summary_text.value = f"Pozostalo: {target_kcal - total_kcal} kcal"

        build_week_chart()

        meals_column.controls.clear()
        for m_type in ["Sniadanie", "II Sniadanie", "Obiad", "Kolacja"]:
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
                                    ft.Container(padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        bgcolor="#1A2A1A", border_radius=6,
                                        content=ft.Text(f"{m_kcal} kcal", size=11, color="#00E676")),
                                    ft.Container(padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        bgcolor="#1A1A2A", border_radius=6,
                                        content=ft.Text(f"B:{m_p}g", size=11, color="#42A5F5")),
                                    ft.Container(padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        bgcolor="#2A1A0A", border_radius=6,
                                        content=ft.Text(f"T:{m_f}g", size=11, color="#FFA726")),
                                    ft.Container(padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        bgcolor="#1E1A2A", border_radius=6,
                                        content=ft.Text(f"W:{m_c}g", size=11, color="#AB47BC")),
                                ], spacing=4, wrap=True)
                            ], expand=True, spacing=4),
                            ft.IconButton(icon="delete_outline", icon_color="#EF5350", icon_size=20,
                                on_click=lambda e, mid=m_id: delete_meal_click(mid))
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    )
                )

            if not items_ui:
                items_ui.append(ft.Container(
                    padding=ft.padding.symmetric(vertical=8),
                    content=ft.Text("Brak wpisow", size=12, color="#444444", italic=True)
                ))

            meals_column.controls.append(
                make_card(ft.Column([
                    ft.Row([
                        ft.Text(m_type, size=15, weight=ft.FontWeight.BOLD, color="#00E676"),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            bgcolor="#1A2A1A", border_radius=8,
                            content=ft.Text(f"{sub_kcal} kcal", size=13,
                                weight=ft.FontWeight.BOLD, color="#00E676")
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=1, color="#2A2A35"),
                    *items_ui
                ]))
            )
        page.update()

    def delete_meal_click(meal_id):
        db.delete_meal(meal_id)
        refresh_diet()

    def add_food_ai_click(e):
        if not food_input.value.strip() and not selected_image_path["path"]:
            show_msg("Opisz posilek lub dodaj zdjecie talerza!", True)
            return
        loading_bar.visible = True
        page.update()
        try:
            res = ai.analyze_food(food_input.value.strip(), selected_image_path["path"])
            db.add_meal(current_date_value[0], meal_type_dd.value,
                res.get("name", "Posilek"), res.get("kcal", 0),
                res.get("protein", 0), res.get("fat", 0), res.get("carbs", 0))
            food_input.value = ""
            selected_image_path["path"] = None
            image_status_txt.value = "Brak zdjecia"
            image_status_txt.color = "#666666"
            refresh_diet()
            show_msg("Dodano posilek wyliczony przez AI!")
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
            db.add_meal(current_date_value[0], meal_type_dd.value,
                res["name"], res["kcal"], res["protein"], res["fat"], res["carbs"])
            barcode_input.value = ""
            refresh_diet()
            show_msg(f"Dodano: {res['name']}")
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
        make_card(ft.Column([
            ft.Row([
                ft.Column([kcal_main_text, diet_summary_text], expand=True),
                ft.Container(width=56, height=56, bgcolor="#1A2A1A", border_radius=28,
                    content=ft.Icon("local_fire_department", color="#00E676", size=28),
                    alignment=ft.alignment.center)
            ]),
            ft.Container(height=8),
            kcal_progress,
            ft.Container(height=10),
            macro_p_txt, macro_p_bar,
            ft.Container(height=6),
            macro_f_txt, macro_f_bar,
            ft.Container(height=6),
            macro_c_txt, macro_c_bar,
        ])),
        # Wykres 7 dni
        make_card(chart_col),
        make_card(ft.Column([
            ft.Row([
                ft.Icon("add_circle_outline", color="#00E676", size=20),
                ft.Text("Dodaj posilek", weight=ft.FontWeight.BOLD, size=15),
            ], spacing=8),
            ft.Container(height=4),
            meal_type_dd,
            food_input,
            ft.Row([
                ft.ElevatedButton("Zdjecie", icon="camera_alt",
                    bgcolor="#1E1E2A", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                        side=ft.BorderSide(1, "#3A3A4A"), elevation=0),
                    on_click=lambda _: file_picker.pick_files(
                        allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)
                ),
                image_status_txt,
            ], spacing=10),
            accent_btn("Policz przez AI i dodaj", "auto_awesome", add_food_ai_click),
            ft.Divider(color="#2A2A35"),
            ft.Row([barcode_input, barcode_weight,
                ft.IconButton(icon="qr_code_scanner", bgcolor="#1565C0", icon_color="white",
                    on_click=add_barcode_click)
            ])
        ])),
        meals_column
    ], visible=True)

    # =========================================================================
    # ZAKŁADKA 2: PRZEPISY + LISTA ZAKUPÓW
    # =========================================================================
    recipe_query = ft.TextField(
        label="Czego szukasz? (np. obiad z kurczakiem do 600 kcal, min 45g bialka)",
        multiline=True,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#1E88E5", border_radius=12,
    )
    recipes_list_col = ft.Column(spacing=8)
    shopping_list_col = ft.Column(spacing=4)
    manual_shop_item = ft.TextField(
        label="Dodaj produkt recznie", expand=True,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )

    # Dialog wyboru posiłku dla przepisu
    recipe_meal_dd = ft.Dropdown(
        label="Dodaj do posilku",
        value="Obiad",
        options=[
            ft.dropdown.Option("Sniadanie"),
            ft.dropdown.Option("II Sniadanie"),
            ft.dropdown.Option("Obiad"),
            ft.dropdown.Option("Kolacja"),
        ],
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676",
    )
    current_recipe_ref = [None]

    eat_recipe_dlg = ft.AlertDialog(
        title=ft.Text("Dodaj przepis do dziennika"),
        content=ft.Column([
            ft.Text("Wybierz do ktorego posilku dodac:", size=13, color="#BDBDBD"),
            recipe_meal_dd,
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Anuluj",
                on_click=lambda e: setattr(eat_recipe_dlg, 'open', False) or page.update()),
            ft.ElevatedButton("Dodaj", bgcolor="#00C853", color="white",
                on_click=lambda e: confirm_eat_recipe(e)),
        ],
        bgcolor="#16161E",
    )
    page.overlay.append(eat_recipe_dlg)

    def confirm_eat_recipe(e):
        rec = current_recipe_ref[0]
        if rec:
            db.add_meal(today_str, recipe_meal_dd.value,
                rec["title"], rec["kcal"], rec["protein"], rec["fat"], rec["carbs"])
            eat_recipe_dlg.open = False
            page.update()
            refresh_diet()
            show_msg(f"Dodano {rec['title']} do {recipe_meal_dd.value}!")

    def open_eat_recipe_dialog(rec):
        current_recipe_ref[0] = rec
        eat_recipe_dlg.open = True
        page.update()

    def save_recipe_to_notes(rec):
        """Eksportuje przepis do schowka w formacie gotowym do wklejenia w Notatkach."""
        ing_text = "\n".join([f"  - {i}" for i in rec["ingredients"]])
        text = (
            f"PRZEPIS: {rec['title']}\n"
            f"Kalorie: {rec['kcal']} kcal | B:{rec['protein']}g T:{rec['fat']}g W:{rec['carbs']}g\n\n"
            f"SKLADNIKI:\n{ing_text}\n\n"
            f"PRZYGOTOWANIE:\n{rec['instructions']}"
        )
        page.set_clipboard(text)
        show_msg("Przepis skopiowany! Wklej w Notatkach lub Google Keep.")

    def save_recipe_to_keep(rec):
        """Kopiuje przepis i otwiera Google Keep."""
        ing_text = "\n".join([f"- {i}" for i in rec["ingredients"]])
        text = (
            f"PRZEPIS: {rec['title']}\n"
            f"Kalorie: {rec['kcal']} kcal | B:{rec['protein']}g T:{rec['fat']}g W:{rec['carbs']}g\n\n"
            f"SKLADNIKI:\n{ing_text}\n\n"
            f"PRZYGOTOWANIE:\n{rec['instructions']}"
        )
        page.set_clipboard(text)
        page.launch_url("https://keep.google.com/")
        show_msg("Skopiowano! Otwieram Google Keep - kliknij Nowa notatka i Wklej.")

    def refresh_recipes_and_shopping():
        recipes_list_col.controls.clear()
        for r in db.get_recipes():
            ing_text = ", ".join(r["ingredients"])
            recipes_list_col.controls.append(
                make_card(ft.Column([
                    ft.Text(r["title"], size=16, weight=ft.FontWeight.BOLD, color="#00E676"),
                    ft.Row([
                        ft.Container(padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            bgcolor="#1A2A1A", border_radius=6,
                            content=ft.Text(f"{r['kcal']} kcal", size=11, color="#00E676")),
                        ft.Container(padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            bgcolor="#1A1A2A", border_radius=6,
                            content=ft.Text(f"B:{r['protein']}g", size=11, color="#42A5F5")),
                        ft.Container(padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            bgcolor="#2A1A0A", border_radius=6,
                            content=ft.Text(f"T:{r['fat']}g", size=11, color="#FFA726")),
                        ft.Container(padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            bgcolor="#1E1A2A", border_radius=6,
                            content=ft.Text(f"W:{r['carbs']}g", size=11, color="#AB47BC")),
                    ], spacing=4, wrap=True),
                    ft.Text(f"Skladniki: {ing_text}", size=12, color="#BDBDBD"),
                    ft.Text(r["instructions"], size=12, color="#757575"),
                    # Przyciski akcji
                    ft.Row([
                        ft.ElevatedButton("Do zakupow", icon="add_shopping_cart",
                            bgcolor="#1E1E2A", color="white",
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                                side=ft.BorderSide(1, "#3A3A4A"), elevation=0),
                            on_click=lambda e, ings=r["ingredients"]: add_ings_to_shop(ings)),
                        ft.ElevatedButton("Dodaj do posilku", icon="restaurant",
                            bgcolor="#1565C0", color="white",
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), elevation=0),
                            on_click=lambda e, rec=r: open_eat_recipe_dialog(rec)),
                    ], wrap=True, spacing=8),
                    ft.Row([
                        ft.ElevatedButton("Zapisz w Notatkach", icon="note_add",
                            bgcolor="#1E1E2A", color="white",
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                                side=ft.BorderSide(1, "#3A3A4A"), elevation=0),
                            on_click=lambda e, rec=r: save_recipe_to_notes(rec)),
                        ft.ElevatedButton("Zapisz w Keep", icon="bookmark_add",
                            bgcolor="#1B5E20", color="white",
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), elevation=0),
                            on_click=lambda e, rec=r: save_recipe_to_keep(rec)),
                    ], wrap=True, spacing=8),
                ], spacing=6))
            )

        shopping_list_col.controls.clear()
        for s_id, item_name, is_checked in db.get_shopping_list():
            shopping_list_col.controls.append(
                ft.Checkbox(label=item_name, value=bool(is_checked), active_color="#00E676",
                    on_change=lambda e, sid=s_id: toggle_shop(sid, e.control.value))
            )
        page.update()

    def add_ings_to_shop(ings):
        db.add_shopping_items(ings)
        refresh_recipes_and_shopping()
        show_msg("Dodano skladniki do listy zakupow!")

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
                db.save_recipe(r.get("title", "Przepis"), r.get("kcal", 0), r.get("protein", 0),
                    r.get("fat", 0), r.get("carbs", 0), r.get("ingredients", []), r.get("instructions", ""))
            refresh_recipes_and_shopping()
            show_msg(f"Pobrano {len(found)} przepisow!")
        except Exception as ex:
            show_msg(str(ex), True)
        finally:
            loading_bar.visible = False
            page.update()

    def export_shopping_list(target):
        items = db.get_shopping_list()
        unchecked = [f"- {i[1]}" for i in items if not i[2]]
        if not unchecked:
            show_msg("Lista zakupow jest pusta!", True)
            return
        formatted_text = "LISTA ZAKUPOW:\n" + "\n".join(unchecked)
        page.set_clipboard(formatted_text)
        if target == "keep":
            page.launch_url("https://keep.google.com/")
            show_msg("Skopiowano! Otwieram Google Keep.")
        else:
            show_msg("Skopiowano liste! Wklej w Notatkach.")

    recipes_view = ft.Column([
        make_header("Przepisy AI i Zakupy"),
        make_card(ft.Column([
            ft.Row([ft.Icon("shopping_cart", color="#00E676", size=20),
                ft.Text("Lista Zakupow", size=15, weight=ft.FontWeight.BOLD)], spacing=8),
            ft.Row([manual_shop_item,
                ft.IconButton(icon="add", bgcolor="#00C853", icon_color="white",
                    on_click=lambda _: (
                        db.add_shopping_items([manual_shop_item.value.strip()]) if manual_shop_item.value.strip() else None,
                        setattr(manual_shop_item, "value", ""),
                        refresh_recipes_and_shopping()
                    ))
            ]),
            shopping_list_col,
            ft.Row([
                ft.ElevatedButton("Google Keep", icon="note_add",
                    bgcolor="#1B5E20", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), elevation=0),
                    on_click=lambda _: export_shopping_list("keep")),
                ft.ElevatedButton("Kopiuj do Notatek", icon="content_copy",
                    bgcolor="#1E1E2A", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                        side=ft.BorderSide(1, "#3A3A4A"), elevation=0),
                    on_click=lambda _: export_shopping_list("ios")),
                ft.TextButton("Wyczysc", style=ft.ButtonStyle(color="#EF5350"),
                    on_click=lambda _: (db.clear_shopping_list(), refresh_recipes_and_shopping()))
            ], wrap=True, spacing=8)
        ])),
        make_card(ft.Column([
            ft.Row([ft.Icon("search", color="#1E88E5", size=20),
                ft.Text("Wyszukiwarka przepisow AI", weight=ft.FontWeight.BOLD, size=15)], spacing=8),
            recipe_query,
            accent_btn("Szukaj przepisow pod makro", "auto_awesome", search_recipes_click, "#1565C0"),
        ])),
        recipes_list_col
    ], visible=False)

    # =========================================================================
    # ZAKŁADKA 3: TRENINGI
    # =========================================================================
    act_type_dd = ft.Dropdown(
        label="Rodzaj aktywnosci", value="Silownia",
        options=[ft.dropdown.Option("Silownia"),
                 ft.dropdown.Option("Inna aktywnosc (Hokej / Kardio / Inne)")],
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676",
    )
    ex_name = ft.TextField(label="Cwiczenie / Aktywnosc",
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    ex_sets = ft.TextField(label="Serie", value="4", width=80,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)
    ex_reps = ft.TextField(label="Powt.", value="8", width=80,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)
    ex_weight = ft.TextField(label="Ciezar (kg)", value="80", width=100,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)
    ex_duration = ft.TextField(label="Czas (min)", value="60", width=100,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)
    ex_kcal = ft.TextField(label="Spalone kcal", value="400", width=110,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)

    workouts_col = ft.Column(spacing=8)
    ai_goal_input = ft.TextField(
        label="Cel dla Trenera AI (np. 4 dni silowni + hokej, progresja w przysiadzie)",
        multiline=True,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#1E88E5", border_radius=12,
    )
    ai_plans_col = ft.Column(spacing=10)

    def refresh_workouts():
        workouts_col.controls.clear()
        for w in db.get_workouts_by_date(current_date_value[0]):
            w_id, w_type, w_name, w_sets, w_reps, w_kg, w_dur, w_kcal, _ = w
            details = f"{w_sets}x{w_reps} | {w_kg}kg" if w_type == "Silownia" else f"{w_dur} min | {w_kcal} kcal"
            workouts_col.controls.append(
                make_card(ft.Row([
                    ft.Container(width=40, height=40, bgcolor="#1A2A1A", border_radius=20,
                        content=ft.Icon("fitness_center" if w_type == "Silownia" else "directions_run",
                            color="#00E676", size=20),
                        alignment=ft.alignment.center),
                    ft.Column([
                        ft.Text(w_name, weight=ft.FontWeight.BOLD, size=14),
                        ft.Text(details, size=12, color="#9E9E9E"),
                    ], expand=True, spacing=2),
                ], spacing=12))
            )

        ai_plans_col.controls.clear()
        for p_id, created, p_name, p_text in db.get_ai_plans():
            ai_plans_col.controls.append(
                make_card(ft.Column([
                    ft.Text(p_name, weight=ft.FontWeight.BOLD, color="#42A5F5", size=15),
                    ft.Text(created, size=11, color="#666666"),
                    ft.Markdown(p_text),
                ]))
            )
        page.update()

    def add_workout_click(e):
        if not ex_name.value.strip():
            show_msg("Podaj nazwe cwiczenia lub aktywnosci!", True)
            return
        db.add_workout(current_date_value[0], act_type_dd.value, ex_name.value.strip(),
            ex_sets.value or 0, ex_reps.value or 0, ex_weight.value or 0,
            ex_duration.value or 0, ex_kcal.value or 0)
        ex_name.value = ""
        refresh_workouts()
        show_msg("Zapisano trening!")

    def generate_plan_click(e):
        if not ai_goal_input.value.strip():
            show_msg("Opisz swoj cel treningowy dla AI!", True)
            return
        loading_bar.visible = True
        page.update()
        try:
            recent = db.get_recent_workouts(limit=30)
            plan_md = ai.generate_workout_plan(ai_goal_input.value.strip(), recent)
            db.save_ai_plan("Plan Treningowy AI", plan_md)
            refresh_workouts()
            show_msg("Trener AI wygenerowac nowa rozpiske!")
        except Exception as ex:
            show_msg(str(ex), True)
        finally:
            loading_bar.visible = False
            page.update()

    workout_view = ft.Column([
        make_header("Dziennik Treningowy"),
        make_card(ft.Column([
            ft.Row([ft.Icon("add_circle_outline", color="#00E676", size=20),
                ft.Text("Zapisz serie / aktywnosc", weight=ft.FontWeight.BOLD, size=15)], spacing=8),
            act_type_dd, ex_name,
            ft.Row([ex_sets, ex_reps, ex_weight], wrap=True, spacing=8),
            ft.Row([ex_duration, ex_kcal], wrap=True, spacing=8),
            accent_btn("Dodaj do dziennika", "fitness_center", add_workout_click),
        ])),
        ft.Container(padding=ft.padding.only(left=16, top=8, bottom=4),
            content=ft.Text("Dzisiejsze aktywnosci:", weight=ft.FontWeight.BOLD, color="#9E9E9E", size=13)),
        workouts_col,
        make_card(ft.Column([
            ft.Row([ft.Icon("auto_awesome", color="#42A5F5", size=20),
                ft.Text("Trener AI - Rozpiska i Progresja", weight=ft.FontWeight.BOLD,
                    size=15, color="#42A5F5")], spacing=8),
            ai_goal_input,
            accent_btn("Generuj plan i progresje ciezaru", "auto_awesome", generate_plan_click, "#1565C0"),
        ])),
        ai_plans_col
    ], visible=False)

    # =========================================================================
    # ZAKŁADKA 4: POSTĘPY I WAGA
    # =========================================================================
    new_weight_input = ft.TextField(
        label="Nowy pomiar wagi (kg)", width=180,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )
    weight_status_txt = ft.Text("", size=24, weight=ft.FontWeight.BOLD, color="white")
    weight_sub_txt = ft.Text("", size=13, color="#9E9E9E")
    weight_history_col = ft.Column(spacing=6)

    def refresh_progress():
        curr_w = float(db.get_setting("current_weight", "90.0") or 90.0)
        targ_w = float(db.get_setting("target_weight", "70.0") or 70.0)
        diff = round(curr_w - targ_w, 1)
        weight_status_txt.value = f"{curr_w} kg"
        weight_sub_txt.value = f"Cel: {targ_w} kg  |  Pozostalo: {diff} kg"

        weight_history_col.controls.clear()
        for w_date, w_val in reversed(db.get_weight_logs()):
            weight_history_col.controls.append(
                make_card(ft.Row([
                    ft.Icon("monitor_weight", color="#9E9E9E", size=18),
                    ft.Text(w_date, color="#BDBDBD", size=13),
                    ft.Text(f"{w_val} kg", weight=ft.FontWeight.BOLD, color="#00E676", size=15),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=10)
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
            show_msg("Wpisz poprawna liczbe!", True)

    progress_view = ft.Column([
        make_header("Twoje Postepy"),
        make_card(ft.Column([
            ft.Row([
                ft.Icon("monitor_weight", color="#00E676", size=24),
                ft.Column([weight_status_txt, weight_sub_txt], spacing=2)
            ], spacing=12),
            ft.Container(height=8),
            ft.Row([new_weight_input, accent_btn("Zapisz", "save", add_weight_click)], spacing=10),
        ])),
        ft.Container(padding=ft.padding.only(left=16, top=8, bottom=4),
            content=ft.Text("Historia pomiarow:", weight=ft.FontWeight.BOLD, color="#9E9E9E", size=13)),
        weight_history_col
    ], visible=False)

    # =========================================================================
    # ZAKŁADKA 5: USTAWIENIA + PROFIL OSOBY
    # =========================================================================
    api_key_field = ft.TextField(
        label="Klucz Google Gemini API",
        password=True, can_reveal_password=True,
        value=db.get_setting("api_key"),
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )
    model_field = ft.TextField(
        label="Nazwa modelu Gemini",
        value=db.get_setting("model_name", "gemini-3.8-flash"),
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12,
    )
    profile_name = ft.TextField(label="Imie", value=db.get_setting("profile_name", ""),
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12)
    profile_age = ft.TextField(label="Wiek (lata)", value=db.get_setting("profile_age", "25"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12, width=120)
    profile_height = ft.TextField(label="Wzrost (cm)", value=db.get_setting("height", "175"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#00E676", border_radius=12, width=120)
    profile_gender = ft.Dropdown(
        label="Plec", value=db.get_setting("profile_gender", "Mezczyzna"),
        options=[ft.dropdown.Option("Mezczyzna"), ft.dropdown.Option("Kobieta")],
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", expand=True)
    profile_activity = ft.Dropdown(
        label="Poziom aktywnosci",
        value=db.get_setting("profile_activity", "Umiarkowanie aktywny"),
        options=[
            ft.dropdown.Option("Siedzacy tryb zycia"),
            ft.dropdown.Option("Lekko aktywny"),
            ft.dropdown.Option("Umiarkowanie aktywny"),
            ft.dropdown.Option("Bardzo aktywny"),
            ft.dropdown.Option("Ekstremalnie aktywny"),
        ],
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676")
    bmr_result_txt = ft.Text("", size=13, color="#9E9E9E")

    t_kcal_field = ft.TextField(label="Cel Kalorii (kcal)", value=db.get_setting("target_kcal", "2200"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    t_prot_field = ft.TextField(label="Cel Bialka (g)", value=db.get_setting("target_protein", "160"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    t_fat_field = ft.TextField(label="Cel Tluszczu (g)", value=db.get_setting("target_fat", "70"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    t_carb_field = ft.TextField(label="Cel Weglowodanow (g)", value=db.get_setting("target_carbs", "230"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    t_weight_field = ft.TextField(label="Docelowa waga (kg)", value=db.get_setting("target_weight", "70.0"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)

    def calc_bmr():
        try:
            age = int(profile_age.value or 25)
            height = float(profile_height.value or 175)
            weight = float(db.get_setting("current_weight", "80") or 80)
            gender = profile_gender.value
            if gender == "Mezczyzna":
                bmr = 10 * weight + 6.25 * height - 5 * age + 5
            else:
                bmr = 10 * weight + 6.25 * height - 5 * age - 161
            activity_map = {
                "Siedzacy tryb zycia": 1.2, "Lekko aktywny": 1.375,
                "Umiarkowanie aktywny": 1.55, "Bardzo aktywny": 1.725,
                "Ekstremalnie aktywny": 1.9,
            }
            factor = activity_map.get(profile_activity.value, 1.55)
            tdee = round(bmr * factor)
            bmr_result_txt.value = f"BMR: {round(bmr)} kcal  |  TDEE: {tdee} kcal/dzien"
            return tdee
        except Exception:
            return None

    def auto_fill_macros(e):
        tdee = calc_bmr()
        if tdee:
            t_kcal_field.value = str(tdee)
            t_prot_field.value = str(round(tdee * 0.30 / 4))
            t_fat_field.value = str(round(tdee * 0.25 / 9))
            t_carb_field.value = str(round(tdee * 0.45 / 4))
            page.update()
            show_msg(f"TDEE: {tdee} kcal - makro uzupelnione!")

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
        show_msg("Ustawienia zapisane!")

    settings_view = ft.Column([
        make_header("Ustawienia"),
        make_card(ft.Column([
            ft.Row([ft.Icon("key", color="#00E676", size=20),
                ft.Text("Konfiguracja AI", weight=ft.FontWeight.BOLD, size=15)], spacing=8),
            api_key_field,
            model_field,
            ft.Text("Modele: gemini-3.8-flash | gemini-2.0-flash-exp | gemini-1.5-flash",
                size=11, color="#666666", italic=True),
        ])),
        make_card(ft.Column([
            ft.Row([ft.Icon("person", color="#42A5F5", size=20),
                ft.Text("Profil osoby", weight=ft.FontWeight.BOLD, size=15)], spacing=8),
            profile_name,
            ft.Row([profile_age, profile_height], spacing=10),
            profile_gender,
            profile_activity,
            ft.ElevatedButton("Wylicz BMR / TDEE automatycznie", icon="calculate",
                bgcolor="#1565C0", color="white",
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), elevation=0),
                on_click=auto_fill_macros),
            bmr_result_txt,
        ])),
        make_card(ft.Column([
            ft.Row([ft.Icon("track_changes", color="#FFA726", size=20),
                ft.Text("Cele i makroskladniki", weight=ft.FontWeight.BOLD, size=15)], spacing=8),
            t_kcal_field,
            ft.Row([t_prot_field, t_fat_field, t_carb_field], wrap=True, spacing=8),
            t_weight_field,
        ])),
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
            ft.NavigationBarDestination(icon="trending_up", label="Postepy"),
            ft.NavigationBarDestination(icon="settings_outlined", selected_icon="settings", label="Ustawienia"),
        ]
    )

    page.add(loading_bar, *views)
    refresh_diet()


ft.app(target=main)
