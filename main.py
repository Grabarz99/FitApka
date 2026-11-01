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
    # HELPERS
    # =========================================================================
    def show_msg(text, is_error=False):
        snack = ft.SnackBar(
            content=ft.Text(text, color="white", weight=ft.FontWeight.W_500),
            bgcolor="#C62828" if is_error else "#2E7D32", duration=3000)
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def make_card(content, padding=14):
        return ft.Container(
            margin=ft.margin.symmetric(horizontal=12, vertical=5),
            padding=padding, bgcolor="#16161E", border_radius=16,
            border=ft.border.all(1, "#2A2A35"), content=content)

    def make_header(title):
        return ft.Container(
            padding=ft.padding.only(left=16, right=16, top=12, bottom=8),
            content=ft.Text(title, size=22, weight=ft.FontWeight.BOLD, color="white"))

    def accent_btn(text, icon, on_click, color="#00C853"):
        return ft.ElevatedButton(text, icon=icon, bgcolor=color, color="white",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), elevation=0),
            on_click=on_click)

    loading_bar = ft.ProgressBar(visible=False, color="#00E676", bgcolor="#1A1A24", height=3)

    # =========================================================================
    # OKNA MODALNE EDYCJI (POSILKI, PRZEPISY, SZABLONY, DZISIEJSZE AKTYWNOSCI)
    # =========================================================================
    def open_edit_meal_dialog(meal_row):
        m_id, m_type, m_name, m_kcal, m_p, m_f, m_c = meal_row

        type_dd = ft.Dropdown(
            label="Posilek", value=m_type,
            options=[ft.dropdown.Option("Sniadanie"), ft.dropdown.Option("II Sniadanie"),
                     ft.dropdown.Option("Obiad"), ft.dropdown.Option("Kolacja")],
            bgcolor="#1E1E2A", border_color="#3A3A4A")
        name_tf = ft.TextField(label="Nazwa posilku", value=m_name, multiline=True,
            bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        kcal_tf = ft.TextField(label="Kcal", value=str(m_kcal), width=110,
            keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        p_tf = ft.TextField(label="Bialko (g)", value=str(m_p), width=110,
            keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        f_tf = ft.TextField(label="Tluszcz (g)", value=str(m_f), width=110,
            keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        c_tf = ft.TextField(label="Wegle (g)", value=str(m_c), width=110,
            keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)

        def scale_portion(factor):
            kcal_tf.value = str(int(round(m_kcal * factor)))
            p_tf.value = str(round(m_p * factor, 1))
            f_tf.value = str(round(m_f * factor, 1))
            c_tf.value = str(round(m_c * factor, 1))
            page.update()

        def save_meal_edit(e):
            try:
                db.update_meal(
                    m_id, type_dd.value, name_tf.value.strip(),
                    int(float(kcal_tf.value.replace(",", ".") or 0)),
                    float(p_tf.value.replace(",", ".") or 0),
                    float(f_tf.value.replace(",", ".") or 0),
                    float(c_tf.value.replace(",", ".") or 0)
                )
                dlg.open = False
                refresh_diet()
                show_msg("Zaktualizowano posilek!")
            except Exception as ex:
                show_msg(f"Blad zapisu: {ex}", True)

        dlg = ft.AlertDialog(
            title=ft.Text("Edytuj posilek"),
            bgcolor="#16161E",
            content=ft.Container(
                width=310,
                content=ft.Column([
                    type_dd, name_tf,
                    ft.Text("Szybki przelicznik porcji:", size=12, color="#9E9E9E"),
                    ft.Row([
                        ft.ElevatedButton("0.5x", bgcolor="#1E1E2A", color="#00E676",
                            on_click=lambda _: scale_portion(0.5)),
                        ft.ElevatedButton("1.5x", bgcolor="#1E1E2A", color="#00E676",
                            on_click=lambda _: scale_portion(1.5)),
                        ft.ElevatedButton("2x", bgcolor="#1E1E2A", color="#00E676",
                            on_click=lambda _: scale_portion(2.0)),
                    ], spacing=6),
                    ft.Row([kcal_tf, p_tf], spacing=8),
                    ft.Row([f_tf, c_tf], spacing=8),
                ], tight=True, spacing=8, scroll=ft.ScrollMode.ADAPTIVE)
            ),
            actions=[
                ft.TextButton("Anuluj", on_click=lambda _: setattr(dlg, "open", False) or page.update()),
                ft.ElevatedButton("Zapisz", bgcolor="#00C853", color="white", on_click=save_meal_edit),
            ]
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def open_edit_recipe_dialog(rec):
        title_tf = ft.TextField(label="Nazwa przepisu", value=rec["title"],
            bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        kcal_tf = ft.TextField(label="Kcal", value=str(rec["kcal"]), width=110,
            keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        p_tf = ft.TextField(label="Bialko (g)", value=str(rec["protein"]), width=110,
            keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        f_tf = ft.TextField(label="Tluszcz (g)", value=str(rec["fat"]), width=110,
            keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        c_tf = ft.TextField(label="Wegle (g)", value=str(rec["carbs"]), width=110,
            keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        ings_tf = ft.TextField(
            label="Skladniki (oddzielone przecinkiem)",
            value=", ".join(rec["ingredients"]),
            multiline=True, min_lines=2, max_lines=4,
            bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        instr_tf = ft.TextField(
            label="Instrukcja przygotowania",
            value=rec["instructions"],
            multiline=True, min_lines=3, max_lines=6,
            bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)

        def save_rec_edit(e):
            try:
                ings_list = [x.strip() for x in ings_tf.value.split(",") if x.strip()]
                db.update_recipe(
                    rec["id"], title_tf.value.strip(),
                    int(float(kcal_tf.value.replace(",", ".") or 0)),
                    float(p_tf.value.replace(",", ".") or 0),
                    float(f_tf.value.replace(",", ".") or 0),
                    float(c_tf.value.replace(",", ".") or 0),
                    ings_list, instr_tf.value.strip()
                )
                dlg.open = False
                refresh_recipes_and_shopping()
                show_msg("Zaktualizowano przepis!")
            except Exception as ex:
                show_msg(f"Blad zapisu: {ex}", True)

        dlg = ft.AlertDialog(
            title=ft.Text("Edytuj przepis"),
            bgcolor="#16161E",
            content=ft.Container(
                width=310,
                content=ft.Column([
                    title_tf,
                    ft.Row([kcal_tf, p_tf], spacing=8),
                    ft.Row([f_tf, c_tf], spacing=8),
                    ings_tf, instr_tf
                ], tight=True, spacing=8, scroll=ft.ScrollMode.ADAPTIVE)
            ),
            actions=[
                ft.TextButton("Anuluj", on_click=lambda _: setattr(dlg, "open", False) or page.update()),
                ft.ElevatedButton("Zapisz", bgcolor="#00C853", color="white", on_click=save_rec_edit),
            ]
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def open_edit_template_dialog(tmpl):
        t_name_tf = ft.TextField(label="Nazwa szablonu", value=tmpl["name"],
            bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        rows_col = ft.Column(spacing=8, scroll=ft.ScrollMode.ADAPTIVE)
        row_controls = []

        def add_exercise_row(ex_name_val="", sets_val="4", reps_val="8", weight_val="80"):
            n_tf = ft.TextField(label="Cwiczenie", value=str(ex_name_val), expand=True,
                bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=8, text_size=12)
            s_tf = ft.TextField(label="S", value=str(sets_val), width=52,
                keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=8, text_size=12)
            r_tf = ft.TextField(label="P", value=str(reps_val), width=52,
                keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=8, text_size=12)
            w_tf = ft.TextField(label="kg", value=str(weight_val), width=68,
                keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=8, text_size=12)

            row_obj = {"n": n_tf, "s": s_tf, "r": r_tf, "w": w_tf, "container": None}

            def remove_this_row(e):
                if row_obj in row_controls:
                    row_controls.remove(row_obj)
                    rows_col.controls.remove(row_obj["container"])
                    page.update()

            del_btn = ft.IconButton(icon="remove_circle_outline", icon_color="#EF5350", icon_size=18, on_click=remove_this_row)
            cont = ft.Container(
                padding=6, bgcolor="#12121A", border_radius=10,
                content=ft.Column([
                    ft.Row([n_tf, del_btn], spacing=4),
                    ft.Row([s_tf, r_tf, w_tf], spacing=6),
                ], spacing=4)
            )
            row_obj["container"] = cont
            row_controls.append(row_obj)
            rows_col.controls.append(cont)
            page.update()

        for ex in tmpl.get("exercises", []):
            add_exercise_row(ex.get("name", ""), ex.get("sets", 4), ex.get("reps", 8), ex.get("weight", 0))

        def save_tmpl_edit(e):
            if not t_name_tf.value.strip():
                show_msg("Podaj nazwe szablonu!", True)
                return
            new_ex_list = []
            for rc in row_controls:
                ename = rc["n"].value.strip()
                if ename:
                    try:
                        s_v = int(float(rc["s"].value.replace(",", ".") or 0))
                        r_v = int(float(rc["r"].value.replace(",", ".") or 0))
                        w_v = float(rc["w"].value.replace(",", ".") or 0.0)
                    except ValueError:
                        s_v, r_v, w_v = 4, 8, 0.0
                    new_ex_list.append({"name": ename, "sets": s_v, "reps": r_v, "weight": w_v})
            db.update_workout_template(tmpl["id"], t_name_tf.value.strip(), new_ex_list)
            dlg.open = False
            refresh_templates()
            show_msg("Zaktualizowano szablon treningu!")

        dlg = ft.AlertDialog(
            title=ft.Text("Edytuj szablon treningu"),
            bgcolor="#16161E",
            content=ft.Container(
                width=320, height=400,
                content=ft.Column([
                    t_name_tf,
                    ft.Row([
                        ft.Text("Cwiczenia w szablonie:", size=12, color="#9E9E9E", expand=True),
                        ft.TextButton("+ Dodaj cwiczenie", on_click=lambda _: add_exercise_row()),
                    ]),
                    rows_col,
                ], scroll=ft.ScrollMode.ADAPTIVE, spacing=8)
            ),
            actions=[
                ft.TextButton("Anuluj", on_click=lambda _: setattr(dlg, "open", False) or page.update()),
                ft.ElevatedButton("Zapisz", bgcolor="#00C853", color="white", on_click=save_tmpl_edit),
            ]
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def open_edit_workout_dialog(w_row):
        w_id, w_type, w_name, w_sets, w_reps, w_kg, w_dur, w_kcal, _ = w_row

        type_dd = ft.Dropdown(
            label="Rodzaj aktywnosci", value=w_type,
            options=[ft.dropdown.Option("Silownia"),
                     ft.dropdown.Option("Inna aktywnosc (Hokej / Kardio / Inne)")],
            bgcolor="#1E1E2A", border_color="#3A3A4A")
        name_tf = ft.TextField(label="Cwiczenie / Aktywnosc", value=w_name,
            bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        sets_tf = ft.TextField(label="Serie", value=str(w_sets), width=90,
            keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        reps_tf = ft.TextField(label="Powt.", value=str(w_reps), width=90,
            keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        kg_tf = ft.TextField(label="Ciezar (kg)", value=str(w_kg), width=110,
            keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        dur_tf = ft.TextField(label="Czas (min)", value=str(w_dur), width=110,
            keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)
        kcal_tf = ft.TextField(label="Spalone kcal", value=str(w_kcal), width=120,
            keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=10)

        def save_w_edit(e):
            try:
                db.update_workout(
                    w_id, type_dd.value, name_tf.value.strip(),
                    int(float(sets_tf.value.replace(",", ".") or 0)),
                    int(float(reps_tf.value.replace(",", ".") or 0)),
                    float(kg_tf.value.replace(",", ".") or 0.0),
                    int(float(dur_tf.value.replace(",", ".") or 0)),
                    int(float(kcal_tf.value.replace(",", ".") or 0))
                )
                dlg.open = False
                refresh_workouts()
                show_msg("Zaktualizowano wpis treningowy!")
            except Exception as ex:
                show_msg(f"Blad zapisu: {ex}", True)

        dlg = ft.AlertDialog(
            title=ft.Text("Edytuj trening"),
            bgcolor="#16161E",
            content=ft.Container(
                width=310,
                content=ft.Column([
                    type_dd, name_tf,
                    ft.Row([sets_tf, reps_tf, kg_tf], wrap=True, spacing=6),
                    ft.Row([dur_tf, kcal_tf], wrap=True, spacing=6),
                ], tight=True, spacing=8)
            ),
            actions=[
                ft.TextButton("Anuluj", on_click=lambda _: setattr(dlg, "open", False) or page.update()),
                ft.ElevatedButton("Zapisz", bgcolor="#00C853", color="white", on_click=save_w_edit),
            ]
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # =========================================================================
    # WIZUALNY KALENDARZ
    # =========================================================================
    cal_year = [datetime.now().year]
    cal_month = [datetime.now().month]
    cal_grid = ft.Column(spacing=2)
    cal_month_label = ft.Text("", size=15, weight=ft.FontWeight.BOLD, color="white")

    def build_calendar():
        import calendar
        cal_grid.controls.clear()
        y, m = cal_year[0], cal_month[0]
        cal_month_label.value = datetime(y, m, 1).strftime("%B %Y")
        days_header = ft.Row([
            ft.Container(width=38, content=ft.Text(d, size=11, color="#666666",
                text_align=ft.TextAlign.CENTER))
            for d in ["Pn", "Wt", "Sr", "Cz", "Pt", "So", "Nd"]
        ], spacing=2)
        cal_grid.controls.append(days_header)

        first_day = datetime(y, m, 1)
        start_offset = first_day.weekday()
        days_in_month = calendar.monthrange(y, m)[1]
        target_kcal = int(db.get_setting("target_kcal", "2200") or 2200)

        week_row = []
        for _ in range(start_offset):
            week_row.append(ft.Container(width=38, height=36))

        for day in range(1, days_in_month + 1):
            date_str = f"{y:04d}-{m:02d}-{day:02d}"
            kcal = db.get_kcal_for_date(date_str)
            is_today = date_str == today_str
            is_selected = date_str == current_date_value[0]

            if is_selected:
                bg = "#00E676"
                txt_color = "#000000"
            elif is_today:
                bg = "#1A2A1A"
                txt_color = "#00E676"
            elif kcal > 0:
                ratio = kcal / max(target_kcal, 1)
                if ratio > 1.05:
                    bg = "#2A1A1A"
                    txt_color = "#EF5350"
                else:
                    bg = "#1A1A2A"
                    txt_color = "#42A5F5"
            else:
                bg = "transparent"
                txt_color = "#9E9E9E"

            def make_day_click(ds):
                def click(e):
                    current_date_value[0] = ds
                    build_calendar()
                    refresh_diet()
                    refresh_workouts()
                    page.update()
                return click

            week_row.append(
                ft.Container(
                    width=38, height=36, bgcolor=bg, border_radius=8,
                    alignment=ft.alignment.center,
                    on_click=make_day_click(date_str),
                    content=ft.Text(str(day), size=13, color=txt_color,
                        weight=ft.FontWeight.BOLD if is_selected or is_today else ft.FontWeight.NORMAL,
                        text_align=ft.TextAlign.CENTER)
                )
            )

            if len(week_row) == 7:
                cal_grid.controls.append(ft.Row(week_row, spacing=2))
                week_row = []

        if week_row:
            while len(week_row) < 7:
                week_row.append(ft.Container(width=38, height=36))
            cal_grid.controls.append(ft.Row(week_row, spacing=2))

    def prev_month(e):
        if cal_month[0] == 1:
            cal_month[0] = 12
            cal_year[0] -= 1
        else:
            cal_month[0] -= 1
        build_calendar()
        page.update()

    def next_month(e):
        if cal_month[0] == 12:
            cal_month[0] = 1
            cal_year[0] += 1
        else:
            cal_month[0] += 1
        build_calendar()
        page.update()

    calendar_widget = make_card(ft.Column([
        ft.Row([
            ft.IconButton(icon="chevron_left", icon_color="#00E676", on_click=prev_month),
            ft.Container(expand=True, content=cal_month_label, alignment=ft.alignment.center),
            ft.IconButton(icon="chevron_right", icon_color="#00E676", on_click=next_month),
        ]),
        cal_grid,
        ft.Row([
            ft.Container(width=12, height=12, bgcolor="#00E676", border_radius=3),
            ft.Text("wybrany", size=10, color="#9E9E9E"),
            ft.Container(width=12, height=12, bgcolor="#1A1A2A", border_radius=3),
            ft.Text("w celu", size=10, color="#9E9E9E"),
            ft.Container(width=12, height=12, bgcolor="#2A1A1A", border_radius=3),
            ft.Text("powyzej celu", size=10, color="#9E9E9E"),
        ], spacing=6, wrap=True)
    ]))

    # =========================================================================
    # ZAKLADKA 1: DIETA
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

    streak_txt = ft.Text("", size=13, color="#FFA726", weight=ft.FontWeight.BOLD)

    water_txt = ft.Text("0 / 8 szklanek", size=14, weight=ft.FontWeight.BOLD, color="#29B6F6")
    water_progress = ft.ProgressBar(value=0, color="#29B6F6", bgcolor="#2A2A35", height=6, border_radius=3)

    def refresh_water():
        glasses = db.get_water_today(current_date_value[0])
        target = int(db.get_setting("target_water", "8") or 8)
        water_txt.value = f"{glasses} / {target} szklanek"
        water_progress.value = min(glasses / max(target, 1), 1.0)

    def add_water(e):
        db.add_water_glass(current_date_value[0])
        refresh_water()
        page.update()

    def remove_water(e):
        db.remove_water_glass(current_date_value[0])
        refresh_water()
        page.update()

    chart_col = ft.Column(spacing=4)

    def build_week_chart():
        chart_col.controls.clear()
        target_kcal = int(db.get_setting("target_kcal", "2200") or 2200)
        days_data = []
        for i in range(6, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            kcal = db.get_kcal_for_date(d)
            label = (datetime.now() - timedelta(days=i)).strftime("%d.%m")
            days_data.append((label, kcal, d == current_date_value[0]))

        max_val = max(max((d[1] for d in days_data), default=0), target_kcal, 1)
        bars = []
        for label, kcal, is_sel in days_data:
            ratio = min(kcal / max_val, 1.0)
            color = "#00E676" if is_sel else ("#EF5350" if kcal > target_kcal else "#42A5F5")
            bars.append(ft.Column([
                ft.Text(str(kcal) if kcal > 0 else "", size=9, color="#9E9E9E",
                    text_align=ft.TextAlign.CENTER),
                ft.Container(width=32, height=max(4, int(55 * ratio)),
                    bgcolor=color, border_radius=ft.border_radius.only(top_left=4, top_right=4)),
                ft.Text(label, size=9, color="#00E676" if is_sel else "#9E9E9E",
                    text_align=ft.TextAlign.CENTER,
                    weight=ft.FontWeight.BOLD if is_sel else ft.FontWeight.NORMAL),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2))

        chart_col.controls.append(ft.Column([
            ft.Row([ft.Icon("bar_chart", color="#42A5F5", size=16),
                ft.Text("Kalorie - ostatnie 7 dni", size=13, weight=ft.FontWeight.BOLD, color="#42A5F5")], spacing=6),
            ft.Container(height=4),
            ft.Row(bars, alignment=ft.MainAxisAlignment.SPACE_AROUND,
                vertical_alignment=ft.CrossAxisAlignment.END),
        ]))

    meals_column = ft.Column(spacing=8)

    meal_type_dd = ft.Dropdown(label="Posilek", value="Sniadanie",
        options=[ft.dropdown.Option("Sniadanie"), ft.dropdown.Option("II Sniadanie"),
                 ft.dropdown.Option("Obiad"), ft.dropdown.Option("Kolacja")],
        expand=True, bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676")
    food_input = ft.TextField(label="Co zjadles? (np. 200g kurczaka i 100g ryzu)",
        multiline=True, min_lines=1, max_lines=3,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    barcode_input = ft.TextField(label="Kod kreskowy", expand=2,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    barcode_weight = ft.TextField(label="Waga (g)", value="100", width=90,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)

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
        diet_summary_text.value = f"Data: {date_val}  |  Pozostalo: {target_kcal - total_kcal} kcal"

        streak = db.get_streak()
        streak_txt.value = f"Streak: {streak} dni z rzedu!" if streak > 0 else ""

        refresh_water()
        build_week_chart()
        build_calendar()

        meals_column.controls.clear()
        for m_type in ["Sniadanie", "II Sniadanie", "Obiad", "Kolacja"]:
            type_meals = [m for m in meals if m[1] == m_type]
            sub_kcal = sum(m[3] for m in type_meals)
            items_ui = []
            for m in type_meals:
                m_id, _, m_name, m_kcal, m_p, m_f, m_c = m
                items_ui.append(ft.Container(
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
                        ft.Row([
                            ft.IconButton(icon="edit_outlined", icon_color="#42A5F5", icon_size=20,
                                tooltip="Edytuj posilek",
                                on_click=lambda e, m_obj=m: open_edit_meal_dialog(m_obj)),
                            ft.IconButton(icon="delete_outline", icon_color="#EF5350", icon_size=20,
                                tooltip="Usun posilek",
                                on_click=lambda e, mid=m_id: (db.delete_meal(mid), refresh_diet())),
                        ], spacing=0)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ))
            if not items_ui:
                items_ui.append(ft.Container(padding=ft.padding.symmetric(vertical=8),
                    content=ft.Text("Brak wpisow", size=12, color="#444444", italic=True)))
            meals_column.controls.append(make_card(ft.Column([
                ft.Row([
                    ft.Text(m_type, size=15, weight=ft.FontWeight.BOLD, color="#00E676"),
                    ft.Container(padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        bgcolor="#1A2A1A", border_radius=8,
                        content=ft.Text(f"{sub_kcal} kcal", size=13,
                            weight=ft.FontWeight.BOLD, color="#00E676"))
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=1, color="#2A2A35"),
                *items_ui
            ])))
        page.update()

    def add_food_ai_click(e):
        if not food_input.value.strip() and not selected_image_path["path"]:
            show_msg("Opisz posilek lub dodaj zdjecie!", True)
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
            show_msg("Dodano posilek!")
        except Exception as ex:
            show_msg(str(ex), True)
        finally:
            loading_bar.visible = False
            page.update()

    def add_barcode_click(e):
        if not barcode_input.value.strip():
            show_msg("Wpisz kod kreskowy!", True)
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

    def analyze_diet_click(e):
        loading_bar.visible = True
        page.update()
        try:
            meals = db.get_meals_by_date(current_date_value[0])
            analysis = ai.analyze_diet(meals)
            show_analysis_dialog(analysis)
        except Exception as ex:
            show_msg(str(ex), True)
        finally:
            loading_bar.visible = False
            page.update()

    analysis_dlg = ft.AlertDialog(
        title=ft.Text("Analiza AI"),
        content=ft.Container(
            width=300, height=400,
            content=ft.Column([ft.Text("", size=13, color="#BDBDBD")], scroll=ft.ScrollMode.AUTO)
        ),
        actions=[ft.ElevatedButton("Zamknij", bgcolor="#1565C0", color="white",
            on_click=lambda e: setattr(analysis_dlg, 'open', False) or page.update())],
        bgcolor="#16161E",
    )
    page.overlay.append(analysis_dlg)

    def show_analysis_dialog(text):
        analysis_dlg.content.content.controls[0].value = text
        analysis_dlg.open = True
        page.update()

    diet_view = ft.Column([
        ft.Container(padding=ft.padding.only(left=16, right=16, top=12, bottom=8),
            content=ft.Row([
                ft.Text("Dziennik Kalorii", size=22, weight=ft.FontWeight.BOLD, color="white", expand=True),
                ft.IconButton(icon="refresh", icon_color="#00E676", on_click=lambda _: refresh_diet()),
            ])),
        calendar_widget,
        make_card(ft.Column([
            ft.Row([
                ft.Column([kcal_main_text, diet_summary_text, streak_txt], expand=True),
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
            ft.Container(height=10),
            ft.Divider(color="#2A2A35"),
            ft.Row([
                ft.Icon("water_drop", color="#29B6F6", size=20),
                ft.Column([water_txt, water_progress], expand=True, spacing=4),
                ft.IconButton(icon="remove", icon_color="#EF5350", on_click=remove_water),
                ft.IconButton(icon="add", icon_color="#29B6F6", on_click=add_water),
            ], spacing=8),
        ])),
        make_card(chart_col),
        make_card(ft.Column([
            ft.Row([ft.Icon("add_circle_outline", color="#00E676", size=20),
                ft.Text("Dodaj posilek", weight=ft.FontWeight.BOLD, size=15)], spacing=8),
            meal_type_dd, food_input,
            ft.Row([
                ft.ElevatedButton("Zdjecie", icon="camera_alt",
                    bgcolor="#1E1E2A", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                        side=ft.BorderSide(1, "#3A3A4A"), elevation=0),
                    on_click=lambda _: file_picker.pick_files(
                        allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)),
                image_status_txt,
            ], spacing=10),
            accent_btn("Policz przez AI i dodaj", "auto_awesome", add_food_ai_click),
            ft.Divider(color="#2A2A35"),
            ft.Row([barcode_input, barcode_weight,
                ft.IconButton(icon="qr_code_scanner", bgcolor="#1565C0", icon_color="white",
                    on_click=add_barcode_click)]),
            ft.Divider(color="#2A2A35"),
            accent_btn("Analizuj dzisiejsza diete AI", "psychology", analyze_diet_click, "#6A1B9A"),
        ])),
        meals_column
    ], visible=True)

    # =========================================================================
    # ZAKLADKA 2: PRZEPISY + LISTA ZAKUPOW
    # =========================================================================
    recipe_query = ft.TextField(
        label="Czego szukasz? (np. obiad z kurczakiem do 600 kcal)",
        multiline=True, bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#1E88E5", border_radius=12)
    recipes_list_col = ft.Column(spacing=8)
    shopping_list_col = ft.Column(spacing=4)
    manual_shop_item = ft.TextField(label="Dodaj produkt recznie", expand=True,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)

    recipe_meal_dd = ft.Dropdown(label="Dodaj do posilku", value="Obiad",
        options=[ft.dropdown.Option("Sniadanie"), ft.dropdown.Option("II Sniadanie"),
                 ft.dropdown.Option("Obiad"), ft.dropdown.Option("Kolacja")],
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676")
    current_recipe_ref = [None]

    eat_recipe_dlg = ft.AlertDialog(
        title=ft.Text("Dodaj przepis do dziennika"),
        content=ft.Column([
            ft.Text("Wybierz do ktorego posilku dodac:", size=13, color="#BDBDBD"),
            recipe_meal_dd,
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Anuluj", on_click=lambda e: setattr(eat_recipe_dlg, 'open', False) or page.update()),
            ft.ElevatedButton("Dodaj", bgcolor="#00C853", color="white",
                on_click=lambda e: confirm_eat_recipe()),
        ],
        bgcolor="#16161E")
    page.overlay.append(eat_recipe_dlg)

    def confirm_eat_recipe():
        rec = current_recipe_ref[0]
        if rec:
            db.add_meal(current_date_value[0], recipe_meal_dd.value,
                rec["title"], rec["kcal"], rec["protein"], rec["fat"], rec["carbs"])
            eat_recipe_dlg.open = False
            page.update()
            refresh_diet()
            show_msg(f"Dodano {rec['title']} do {recipe_meal_dd.value}!")

    def save_recipe_to_notes(rec):
        ing_text = "\n".join([f"  - {i}" for i in rec["ingredients"]])
        text = (f"PRZEPIS: {rec['title']}\n"
                f"Kalorie: {rec['kcal']} kcal | B:{rec['protein']}g T:{rec['fat']}g W:{rec['carbs']}g\n\n"
                f"SKLADNIKI:\n{ing_text}\n\nPRZYGOTOWANIE:\n{rec['instructions']}")
        page.set_clipboard(text)
        show_msg("Przepis skopiowany! Wklej w Notatkach.")

    def save_recipe_to_keep(rec):
        ing_text = "\n".join([f"- {i}" for i in rec["ingredients"]])
        text = (f"PRZEPIS: {rec['title']}\n"
                f"Kalorie: {rec['kcal']} kcal\n\nSKLADNIKI:\n{ing_text}\n\nPRZYGOTOWANIE:\n{rec['instructions']}")
        page.set_clipboard(text)
        page.launch_url("https://keep.google.com/")
        show_msg("Skopiowano! Otwieram Google Keep.")

    def refresh_recipes_and_shopping():
        recipes_list_col.controls.clear()
        for r in db.get_recipes():
            ing_text = ", ".join(r["ingredients"])
            recipes_list_col.controls.append(make_card(ft.Column([
                ft.Row([
                    ft.Text(r["title"], size=16, weight=ft.FontWeight.BOLD, color="#00E676", expand=True),
                    ft.IconButton(icon="edit_outlined", icon_color="#42A5F5", icon_size=20,
                        tooltip="Edytuj przepis",
                        on_click=lambda e, rec=r: open_edit_recipe_dialog(rec)),
                    ft.IconButton(icon="delete_outline", icon_color="#EF5350", icon_size=20,
                        tooltip="Usun przepis",
                        on_click=lambda e, rid=r["id"]: (
                            db.delete_recipe(rid), refresh_recipes_and_shopping())),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
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
                ft.Row([
                    ft.ElevatedButton("Do zakupow", icon="add_shopping_cart",
                        bgcolor="#1E1E2A", color="white",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                            side=ft.BorderSide(1, "#3A3A4A"), elevation=0),
                        on_click=lambda e, ings=r["ingredients"]: (
                            db.add_shopping_items(ings), refresh_recipes_and_shopping(),
                            show_msg("Dodano do zakupow!"))),
                    ft.ElevatedButton("Dodaj do posilku", icon="restaurant",
                        bgcolor="#1565C0", color="white",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), elevation=0),
                        on_click=lambda e, rec=r: (
                            current_recipe_ref.__setitem__(0, rec),
                            setattr(eat_recipe_dlg, 'open', True),
                            page.update())),
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
            ], spacing=6)))

        shopping_list_col.controls.clear()
        for s_id, item_name, is_checked in db.get_shopping_list():
            shopping_list_col.controls.append(
                ft.Checkbox(label=item_name, value=bool(is_checked), active_color="#00E676",
                    on_change=lambda e, sid=s_id: db.toggle_shopping_item(sid, e.control.value) or refresh_recipes_and_shopping()))
        page.update()

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
        text = "LISTA ZAKUPOW:\n" + "\n".join(unchecked)
        page.set_clipboard(text)
        if target == "keep":
            page.launch_url("https://keep.google.com/")
            show_msg("Skopiowano! Otwieram Google Keep.")
        else:
            show_msg("Skopiowano liste!")

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
                        refresh_recipes_and_shopping()))]),
            shopping_list_col,
            ft.Row([
                ft.ElevatedButton("Google Keep", icon="note_add", bgcolor="#1B5E20", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), elevation=0),
                    on_click=lambda _: export_shopping_list("keep")),
                ft.ElevatedButton("Kopiuj", icon="content_copy", bgcolor="#1E1E2A", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                        side=ft.BorderSide(1, "#3A3A4A"), elevation=0),
                    on_click=lambda _: export_shopping_list("ios")),
                ft.TextButton("Wyczysc", style=ft.ButtonStyle(color="#EF5350"),
                    on_click=lambda _: (db.clear_shopping_list(), refresh_recipes_and_shopping()))
            ], wrap=True, spacing=8)])),
        make_card(ft.Column([
            ft.Row([ft.Icon("search", color="#1E88E5", size=20),
                ft.Text("Wyszukiwarka przepisow AI", weight=ft.FontWeight.BOLD, size=15)], spacing=8),
            recipe_query,
            accent_btn("Szukaj przepisow pod makro", "auto_awesome", search_recipes_click, "#1565C0"),
        ])),
        recipes_list_col
    ], visible=False)

    # =========================================================================
    # ZAKLADKA 3: TRENINGI + TIMER + SZABLONY + 1RM
    # =========================================================================
    act_type_dd = ft.Dropdown(label="Rodzaj aktywnosci", value="Silownia",
        options=[ft.dropdown.Option("Silownia"),
                 ft.dropdown.Option("Inna aktywnosc (Hokej / Kardio / Inne)")],
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676")
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
    ex_kcal_field = ft.TextField(label="Spalone kcal", value="400", width=110,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)

    timer_seconds = [90]
    timer_running = [False]
    timer_display = ft.Text("1:30", size=32, weight=ft.FontWeight.BOLD, color="#00E676",
        text_align=ft.TextAlign.CENTER)
    timer_progress = ft.ProgressBar(value=1.0, color="#00E676", bgcolor="#2A2A35", height=8, border_radius=4)
    timer_total = [90]

    def timer_tick():
        import threading
        if timer_running[0] and timer_seconds[0] > 0:
            timer_seconds[0] -= 1
            mins = timer_seconds[0] // 60
            secs = timer_seconds[0] % 60
            timer_display.value = f"{mins}:{secs:02d}"
            timer_progress.value = timer_seconds[0] / max(timer_total[0], 1)
            if timer_seconds[0] == 0:
                timer_running[0] = False
                timer_display.color = "#EF5350"
                timer_display.value = "CZAS!"
                show_msg("Przerwa skonczona! Czas na kolejna serie!")
            page.update()
            if timer_running[0]:
                t = threading.Timer(1.0, timer_tick)
                t.daemon = True
                t.start()

    def start_timer(e):
        import threading
        if not timer_running[0]:
            timer_running[0] = True
            timer_display.color = "#00E676"
            t = threading.Timer(1.0, timer_tick)
            t.daemon = True
            t.start()
            page.update()

    def stop_timer(e):
        timer_running[0] = False
        page.update()

    def reset_timer(secs):
        timer_running[0] = False
        timer_seconds[0] = secs
        timer_total[0] = secs
        mins = secs // 60
        s = secs % 60
        timer_display.value = f"{mins}:{s:02d}"
        timer_display.color = "#00E676"
        timer_progress.value = 1.0
        page.update()

    rm_weight = ft.TextField(label="Ciezar (kg)", value="100", width=120,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)
    rm_reps = ft.TextField(label="Powt.", value="5", width=80,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)
    rm_result = ft.Text("", size=18, weight=ft.FontWeight.BOLD, color="#00E676")

    def calc_1rm(e):
        try:
            result = ai.calculate_1rm(float(rm_weight.value or 0), float(rm_reps.value or 1))
            rm_result.value = f"Szacowane 1RM: {result} kg"
            page.update()
        except Exception:
            show_msg("Wpisz poprawne wartosci!", True)

    template_name_field = ft.TextField(label="Nazwa szablonu", expand=True,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    templates_col = ft.Column(spacing=6)

    def save_template(e):
        if not template_name_field.value.strip():
            show_msg("Podaj nazwe szablonu!", True)
            return
        exercises = db.get_workouts_by_date(current_date_value[0])
        if not exercises:
            show_msg("Najpierw dodaj dzisiejsze cwiczenia lub utworz pusty szablon!", True)
            return
        ex_list = [{"name": w[2], "sets": w[3], "reps": w[4], "weight": w[5]} for w in exercises]
        db.save_workout_template(template_name_field.value.strip(), ex_list)
        template_name_field.value = ""
        refresh_templates()
        show_msg("Szablon zapisany!")

    def refresh_templates():
        templates_col.controls.clear()
        for t in db.get_workout_templates():
            ex_names = ", ".join([f"{ex['name']} ({ex.get('sets',4)}x{ex.get('reps',8)})" for ex in t["exercises"]])
            templates_col.controls.append(make_card(ft.Row([
                ft.Column([
                    ft.Text(t["name"], weight=ft.FontWeight.BOLD, size=14, color="#00E676"),
                    ft.Text(ex_names or "Brak cwiczen", size=12, color="#9E9E9E"),
                ], expand=True),
                ft.ElevatedButton("Uzyj", bgcolor="#1565C0", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), elevation=0),
                    on_click=lambda e, tmpl=t: use_template(tmpl)),
                ft.IconButton(icon="edit_outlined", icon_color="#42A5F5", icon_size=20,
                    tooltip="Edytuj szablon",
                    on_click=lambda e, tmpl=t: open_edit_template_dialog(tmpl)),
                ft.IconButton(icon="delete_outline", icon_color="#EF5350", icon_size=20,
                    tooltip="Usun szablon",
                    on_click=lambda e, tid=t["id"]: (
                        db.delete_workout_template(tid), refresh_templates())),
            ], spacing=4), padding=10))
        page.update()

    def use_template(tmpl):
        for ex in tmpl["exercises"]:
            db.add_workout(current_date_value[0], "Silownia",
                ex["name"], ex["sets"], ex["reps"], ex["weight"], 0, 0)
        refresh_workouts()
        show_msg(f"Zaladowano szablon: {tmpl['name']}!")

    workouts_col = ft.Column(spacing=8)
    ai_goal_input = ft.TextField(
        label="Cel dla Trenera AI (np. 4 dni silowni + hokej, progresja w przysiadzie)",
        multiline=True, bgcolor="#1E1E2A", border_color="#3A3A4A",
        focused_border_color="#1E88E5", border_radius=12)
    ai_plans_col = ft.Column(spacing=10)

    def refresh_workouts():
        workouts_col.controls.clear()
        for w in db.get_workouts_by_date(current_date_value[0]):
            w_id, w_type, w_name, w_sets, w_reps, w_kg, w_dur, w_kcal, _ = w
            details = f"{w_sets}x{w_reps} | {w_kg}kg" if w_type == "Silownia" else f"{w_dur} min | {w_kcal} kcal"
            workouts_col.controls.append(make_card(ft.Row([
                ft.Container(width=40, height=40, bgcolor="#1A2A1A", border_radius=20,
                    content=ft.Icon("fitness_center" if w_type == "Silownia" else "directions_run",
                        color="#00E676", size=20), alignment=ft.alignment.center),
                ft.Column([
                    ft.Text(w_name, weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(details, size=12, color="#9E9E9E"),
                ], expand=True, spacing=2),
                ft.Row([
                    ft.IconButton(icon="edit_outlined", icon_color="#42A5F5", icon_size=20,
                        tooltip="Edytuj serie / cwiczenie",
                        on_click=lambda e, w_obj=w: open_edit_workout_dialog(w_obj)),
                    ft.IconButton(icon="delete_outline", icon_color="#EF5350", icon_size=20,
                        tooltip="Usun cwiczenie",
                        on_click=lambda e, wid=w_id: (db.delete_workout(wid), refresh_workouts())),
                ], spacing=0),
            ], spacing=10)))

        ai_plans_col.controls.clear()
        for p_id, created, p_name, p_text in db.get_ai_plans():
            ai_plans_col.controls.append(make_card(ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text(p_name, weight=ft.FontWeight.BOLD, color="#42A5F5", size=15),
                        ft.Text(created, size=11, color="#666666"),
                    ], expand=True),
                    ft.IconButton(icon="delete_outline", icon_color="#EF5350", icon_size=20,
                        on_click=lambda e, pid=p_id: (db.delete_ai_plan(pid), refresh_workouts())),
                ]),
                ft.Markdown(p_text),
            ])))
        refresh_templates()
        page.update()

    def add_workout_click(e):
        if not ex_name.value.strip():
            show_msg("Podaj nazwe cwiczenia!", True)
            return
        db.add_workout(current_date_value[0], act_type_dd.value, ex_name.value.strip(),
            ex_sets.value or 0, ex_reps.value or 0, ex_weight.value or 0,
            ex_duration.value or 0, ex_kcal_field.value or 0)
        ex_name.value = ""
        refresh_workouts()
        show_msg("Zapisano trening!")

    def generate_plan_click(e):
        if not ai_goal_input.value.strip():
            show_msg("Opisz swoj cel treningowy!", True)
            return
        loading_bar.visible = True
        page.update()
        try:
            recent = db.get_recent_workouts(limit=30)
            plan_md = ai.generate_workout_plan(ai_goal_input.value.strip(), recent)
            db.save_ai_plan("Plan Treningowy AI", plan_md)
            refresh_workouts()
            show_msg("Trener AI wygenerowal nowa rozpiske!")
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
            ft.Row([ex_duration, ex_kcal_field], wrap=True, spacing=8),
            accent_btn("Dodaj do dziennika", "fitness_center", add_workout_click),
        ])),
        make_card(ft.Column([
            ft.Row([ft.Icon("timer", color="#FFA726", size=20),
                ft.Text("Timer przerwy miedzy seriami", weight=ft.FontWeight.BOLD, size=15,
                    color="#FFA726")], spacing=8),
            ft.Container(alignment=ft.alignment.center, content=timer_display),
            timer_progress,
            ft.Row([
                ft.ElevatedButton("30s", bgcolor="#1E1E2A", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                        side=ft.BorderSide(1, "#3A3A4A"), elevation=0),
                    on_click=lambda _: reset_timer(30)),
                ft.ElevatedButton("60s", bgcolor="#1E1E2A", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                        side=ft.BorderSide(1, "#3A3A4A"), elevation=0),
                    on_click=lambda _: reset_timer(60)),
                ft.ElevatedButton("90s", bgcolor="#1E1E2A", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                        side=ft.BorderSide(1, "#3A3A4A"), elevation=0),
                    on_click=lambda _: reset_timer(90)),
                ft.ElevatedButton("2min", bgcolor="#1E1E2A", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                        side=ft.BorderSide(1, "#3A3A4A"), elevation=0),
                    on_click=lambda _: reset_timer(120)),
            ], wrap=True, spacing=8),
            ft.Row([
                accent_btn("START", "play_arrow", start_timer, "#00C853"),
                ft.ElevatedButton("STOP", icon="stop", bgcolor="#C62828", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), elevation=0),
                    on_click=stop_timer),
            ], spacing=10),
        ])),
        make_card(ft.Column([
            ft.Row([ft.Icon("calculate", color="#42A5F5", size=20),
                ft.Text("Kalkulator 1RM", weight=ft.FontWeight.BOLD, size=15, color="#42A5F5")], spacing=8),
            ft.Row([rm_weight, rm_reps,
                ft.ElevatedButton("Oblicz", bgcolor="#1565C0", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), elevation=0),
                    on_click=calc_1rm)], spacing=10),
            rm_result,
        ])),
        make_card(ft.Column([
            ft.Row([ft.Icon("bookmark", color="#AB47BC", size=20),
                ft.Text("Szablony treningow", weight=ft.FontWeight.BOLD, size=15, color="#AB47BC")], spacing=8),
            ft.Row([template_name_field,
                ft.ElevatedButton("Zapisz dzis", bgcolor="#6A1B9A", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), elevation=0),
                    on_click=save_template)], spacing=8),
            templates_col,
        ])),
        ft.Container(padding=ft.padding.only(left=16, top=8, bottom=4),
            content=ft.Text("Dzisiejsze aktywnosci:", weight=ft.FontWeight.BOLD, color="#9E9E9E", size=13)),
        workouts_col,
        make_card(ft.Column([
            ft.Row([ft.Icon("auto_awesome", color="#42A5F5", size=20),
                ft.Text("Trener AI", weight=ft.FontWeight.BOLD, size=15, color="#42A5F5")], spacing=8),
            ai_goal_input,
            accent_btn("Generuj plan i progresje", "auto_awesome", generate_plan_click, "#1565C0"),
        ])),
        ai_plans_col
    ], visible=False)

    # =========================================================================
    # ZAKLADKA 4: POSTEPY – WAGA + ZDJECIA + BMI + POROWNANIE
    # =========================================================================
    new_weight_input = ft.TextField(label="Nowy pomiar wagi (kg)", width=180,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    weight_status_txt = ft.Text("", size=24, weight=ft.FontWeight.BOLD, color="white")
    weight_sub_txt = ft.Text("", size=13, color="#9E9E9E")
    bmi_txt = ft.Text("", size=14, color="#FFA726", weight=ft.FontWeight.BOLD)
    weight_history_col = ft.Column(spacing=6)
    weight_chart_col = ft.Column(spacing=4)
    photos_col = ft.Column(spacing=8)
    comparison_col = ft.Column(spacing=4)

    def build_weight_chart():
        weight_chart_col.controls.clear()
        logs = db.get_weight_logs()
        if len(logs) < 2:
            weight_chart_col.controls.append(
                ft.Text("Dodaj wiecej pomiarow aby zobaczyc wykres", size=12, color="#666666", italic=True))
            return
        recent = logs[-10:]
        min_w = min(w for _, w in recent)
        max_w = max(w for _, w in recent)
        diff = max(max_w - min_w, 0.1)
        bars = []
        for date_str, w in recent:
            ratio = (w - min_w) / diff
            label = date_str[5:]
            bars.append(ft.Column([
                ft.Text(f"{w}", size=9, color="#9E9E9E", text_align=ft.TextAlign.CENTER),
                ft.Container(width=28, height=max(8, int(60 * ratio)),
                    bgcolor="#00E676", border_radius=ft.border_radius.only(top_left=4, top_right=4)),
                ft.Text(label, size=8, color="#9E9E9E", text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2))

        weight_chart_col.controls.append(ft.Column([
            ft.Row([ft.Icon("show_chart", color="#00E676", size=16),
                ft.Text("Historia wagi (ostatnie 10)", size=13, weight=ft.FontWeight.BOLD, color="#00E676")], spacing=6),
            ft.Container(height=4),
            ft.Row(bars, alignment=ft.MainAxisAlignment.SPACE_AROUND,
                vertical_alignment=ft.CrossAxisAlignment.END),
        ]))

    def build_comparison():
        comparison_col.controls.clear()
        this_week_start = datetime.now().date() - timedelta(days=datetime.now().weekday())
        last_week_start = this_week_start - timedelta(days=7)

        this_kcal, last_kcal = 0, 0
        this_workouts, last_workouts = 0, 0
        for i in range(7):
            d1 = (this_week_start + timedelta(days=i)).strftime("%Y-%m-%d")
            d2 = (last_week_start + timedelta(days=i)).strftime("%Y-%m-%d")
            this_kcal += db.get_kcal_for_date(d1)
            last_kcal += db.get_kcal_for_date(d2)
            this_workouts += len(db.get_workouts_by_date(d1))
            last_workouts += len(db.get_workouts_by_date(d2))

        def diff_icon(a, b):
            if a > b: return ("arrow_upward", "#00E676")
            if a < b: return ("arrow_downward", "#EF5350")
            return ("remove", "#9E9E9E")

        kcal_icon, kcal_color = diff_icon(this_kcal, last_kcal)
        work_icon, work_color = diff_icon(this_workouts, last_workouts)

        comparison_col.controls.append(ft.Column([
            ft.Row([ft.Icon("compare_arrows", color="#42A5F5", size=16),
                ft.Text("Ten tydzien vs poprzedni", size=13, weight=ft.FontWeight.BOLD, color="#42A5F5")], spacing=6),
            ft.Row([
                ft.Column([
                    ft.Text("Ten tydzien", size=11, color="#9E9E9E"),
                    ft.Text(f"{this_kcal} kcal", size=16, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text(f"{this_workouts} serii", size=12, color="#9E9E9E"),
                ], expand=True),
                ft.Column([
                    ft.Icon(kcal_icon, color=kcal_color, size=24),
                    ft.Icon(work_icon, color=work_color, size=20),
                ]),
                ft.Column([
                    ft.Text("Poprzedni", size=11, color="#9E9E9E"),
                    ft.Text(f"{last_kcal} kcal", size=16, weight=ft.FontWeight.BOLD, color="#9E9E9E"),
                    ft.Text(f"{last_workouts} serii", size=12, color="#9E9E9E"),
                ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.END),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ]))

    def refresh_progress():
        curr_w = float(db.get_setting("current_weight", "90.0") or 90.0)
        targ_w = float(db.get_setting("target_weight", "70.0") or 70.0)
        height_cm = float(db.get_setting("height", "163") or 163)
        diff = round(curr_w - targ_w, 1)
        weight_status_txt.value = f"{curr_w} kg"
        weight_sub_txt.value = f"Cel: {targ_w} kg  |  Pozostalo: {diff} kg"

        h_m = height_cm / 100
        bmi = round(curr_w / (h_m * h_m), 1)
        if bmi < 18.5: bmi_cat = "Niedowaga"
        elif bmi < 25: bmi_cat = "Norma"
        elif bmi < 30: bmi_cat = "Nadwaga"
        else: bmi_cat = "Otylosc"
        bmi_txt.value = f"BMI: {bmi} ({bmi_cat})"

        build_weight_chart()
        build_comparison()

        weight_history_col.controls.clear()
        for log_id, w_date, w_val in reversed(db.get_weight_logs_with_id()):
            weight_history_col.controls.append(make_card(ft.Row([
                ft.Icon("monitor_weight", color="#9E9E9E", size=18),
                ft.Text(w_date, color="#BDBDBD", size=13, expand=True),
                ft.Text(f"{w_val} kg", weight=ft.FontWeight.BOLD, color="#00E676", size=15),
                ft.IconButton(icon="delete_outline", icon_color="#EF5350", icon_size=18,
                    on_click=lambda e, lid=log_id: (db.delete_weight_log(lid), refresh_progress())),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=10))

        photos_col.controls.clear()
        for p_id, p_date, p_path, p_note in db.get_progress_photos():
            photos_col.controls.append(make_card(ft.Row([
                ft.Icon("photo", color="#42A5F5", size=24),
                ft.Column([
                    ft.Text(p_date, size=13, weight=ft.FontWeight.BOLD),
                    ft.Text(p_note or "Brak opisu", size=12, color="#9E9E9E"),
                ], expand=True),
                ft.IconButton(icon="delete_outline", icon_color="#EF5350",
                    on_click=lambda e, pid=p_id: (db.delete_progress_photo(pid), refresh_progress())),
            ], spacing=10), padding=10))

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

    photo_note_field = ft.TextField(label="Opis zdjecia (opcjonalnie)", expand=True,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    selected_progress_photo = {"path": None}
    progress_photo_status = ft.Text("Brak zdjecia", size=12, italic=True, color="#666666")

    def on_progress_photo_picked(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            selected_progress_photo["path"] = e.files[0].path
            progress_photo_status.value = f"OK: {e.files[0].name}"
            progress_photo_status.color = "#00E676"
        else:
            selected_progress_photo["path"] = None
            progress_photo_status.value = "Brak zdjecia"
            progress_photo_status.color = "#666666"
        page.update()

    progress_photo_picker = ft.FilePicker(on_result=on_progress_photo_picked)
    page.overlay.append(progress_photo_picker)

    def save_progress_photo(e):
        if not selected_progress_photo["path"]:
            show_msg("Wybierz zdjecie!", True)
            return
        db.add_progress_photo(today_str, selected_progress_photo["path"], photo_note_field.value.strip())
        selected_progress_photo["path"] = None
        progress_photo_status.value = "Brak zdjecia"
        progress_photo_status.color = "#666666"
        photo_note_field.value = ""
        refresh_progress()
        show_msg("Zdjecie sylwetki zapisane!")

    def analyze_photo_click(e):
        if not selected_progress_photo["path"]:
            show_msg("Wybierz zdjecie sylwetki!", True)
            return
        loading_bar.visible = True
        page.update()
        try:
            analysis = ai.analyze_progress_photo(selected_progress_photo["path"])
            show_analysis_dialog(analysis)
        except Exception as ex:
            show_msg(str(ex), True)
        finally:
            loading_bar.visible = False
            page.update()

    progress_view = ft.Column([
        make_header("Twoje Postepy"),
        make_card(ft.Column([
            ft.Row([
                ft.Icon("monitor_weight", color="#00E676", size=24),
                ft.Column([weight_status_txt, weight_sub_txt, bmi_txt], spacing=2)
            ], spacing=12),
            ft.Container(height=8),
            ft.Row([new_weight_input, accent_btn("Zapisz", "save", add_weight_click)], spacing=10),
        ])),
        make_card(weight_chart_col),
        make_card(comparison_col),
        make_card(ft.Column([
            ft.Row([ft.Icon("photo_camera", color="#42A5F5", size=20),
                ft.Text("Zdjecia sylwetki", weight=ft.FontWeight.BOLD, size=15, color="#42A5F5")], spacing=8),
            ft.Row([
                ft.ElevatedButton("Wybierz zdjecie", icon="add_photo_alternate",
                    bgcolor="#1E1E2A", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                        side=ft.BorderSide(1, "#3A3A4A"), elevation=0),
                    on_click=lambda _: progress_photo_picker.pick_files(
                        allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)),
                progress_photo_status,
            ], spacing=10),
            photo_note_field,
            ft.Row([
                accent_btn("Zapisz zdjecie", "save", save_progress_photo, "#1565C0"),
                accent_btn("Analizuj AI", "psychology", analyze_photo_click, "#6A1B9A"),
            ], spacing=10),
            photos_col,
        ])),
        ft.Container(padding=ft.padding.only(left=16, top=8, bottom=4),
            content=ft.Text("Historia pomiarow:", weight=ft.FontWeight.BOLD, color="#9E9E9E", size=13)),
        weight_history_col
    ], visible=False)

    # =========================================================================
    # ZAKLADKA 5: AI CHAT
    # =========================================================================
    chat_messages_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=380)
    chat_input = ft.TextField(label="Zapytaj dietetyka AI...", expand=True,
        multiline=True, min_lines=1, max_lines=3,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    motivation_txt = ft.Text("", size=13, color="#BDBDBD", italic=True)

    def refresh_chat():
        chat_messages_col.controls.clear()
        history = db.get_chat_history(limit=30)
        for role, msg, created_at in reversed(history):
            is_user = role == "user"
            chat_messages_col.controls.append(
                ft.Row([
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        bgcolor="#1565C0" if is_user else "#1E1E2A",
                        border_radius=ft.border_radius.only(
                            top_left=12, top_right=12,
                            bottom_left=0 if is_user else 12,
                            bottom_right=12 if is_user else 0),
                        content=ft.Column([
                            ft.Text(msg, size=13, color="white"),
                            ft.Text(created_at[11:16], size=10, color="#9E9E9E"),
                        ], spacing=2),
                        expand=True,
                    )
                ], alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START)
            )
        page.update()

    def send_chat_click(e):
        msg = chat_input.value.strip()
        if not msg:
            return
        chat_input.value = ""
        db.save_chat_message("user", msg)
        refresh_chat()
        loading_bar.visible = True
        page.update()
        try:
            history = db.get_chat_history(limit=10)
            response = ai.chat(msg, history)
            db.save_chat_message("ai", response)
            refresh_chat()
        except Exception as ex:
            show_msg(str(ex), True)
        finally:
            loading_bar.visible = False
            page.update()

    def get_motivation_click(e):
        loading_bar.visible = True
        page.update()
        try:
            mot = ai.get_daily_motivation()
            motivation_txt.value = mot
            page.update()
        except Exception as ex:
            show_msg(str(ex), True)
        finally:
            loading_bar.visible = False
            page.update()

    chat_view = ft.Column([
        make_header("AI Dietetyk i Trener"),
        make_card(ft.Column([
            ft.Row([ft.Icon("wb_sunny", color="#FFA726", size=20),
                ft.Text("Motywacja na dzis", weight=ft.FontWeight.BOLD, size=15, color="#FFA726")], spacing=8),
            motivation_txt,
            accent_btn("Pobierz motywacje i porade", "auto_awesome", get_motivation_click, "#E65100"),
        ])),
        make_card(ft.Column([
            ft.Row([ft.Icon("chat", color="#00E676", size=20),
                ft.Text("Chatbot dietetyczny", weight=ft.FontWeight.BOLD, size=15)], spacing=8),
            ft.Text("Zapytaj o diete, trening, przepisy, makro...", size=12, color="#666666", italic=True),
            chat_messages_col,
            ft.Row([
                chat_input,
                ft.IconButton(icon="send", bgcolor="#00C853", icon_color="white",
                    on_click=send_chat_click),
            ], spacing=8),
            ft.TextButton("Wyczysc chat", style=ft.ButtonStyle(color="#EF5350"),
                on_click=lambda _: (db.clear_chat_history(), refresh_chat())),
        ])),
    ], visible=False)

    # =========================================================================
    # ZAKLADKA 6: PROFIL I OPCJE (USTAWIENIA + BACKUP MIEDZY TELEFONAMI)
    # =========================================================================
    api_key_field = ft.TextField(label="Klucz Google Gemini API",
        password=True, can_reveal_password=True, value=db.get_setting("api_key"),
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    model_field = ft.TextField(label="Nazwa modelu Gemini",
        value=db.get_setting("model_name", "gemini-2.5-flash"),
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    profile_name = ft.TextField(label="Imie", value=db.get_setting("profile_name", ""),
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    profile_age = ft.TextField(label="Wiek (lata)", value=db.get_setting("profile_age", "24"),
        keyboard_type=ft.KeyboardType.NUMBER, width=120,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    profile_height = ft.TextField(label="Wzrost (cm)", value=db.get_setting("height", "163"),
        keyboard_type=ft.KeyboardType.NUMBER, width=120,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)
    profile_gender = ft.Dropdown(label="Plec", value=db.get_setting("profile_gender", "Mezczyzna"),
        options=[ft.dropdown.Option("Mezczyzna"), ft.dropdown.Option("Kobieta")],
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", expand=True)
    profile_activity = ft.Dropdown(label="Poziom aktywnosci",
        value=db.get_setting("profile_activity", "Umiarkowanie aktywny"),
        options=[ft.dropdown.Option("Siedzacy tryb zycia"), ft.dropdown.Option("Lekko aktywny"),
                 ft.dropdown.Option("Umiarkowanie aktywny"), ft.dropdown.Option("Bardzo aktywny"),
                 ft.dropdown.Option("Ekstremalnie aktywny")],
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
    t_water_field = ft.TextField(label="Cel wody (szklanki/dzien)", value=db.get_setting("target_water", "8"),
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1E1E2A", border_color="#3A3A4A", focused_border_color="#00E676", border_radius=12)

    backup_json_tf = ft.TextField(
        label="Wklej tutaj skopiowany kod backupu JSON (do importu)",
        multiline=True, min_lines=2, max_lines=4,
        bgcolor="#1E1E2A", border_color="#3A3A4A", border_radius=12)

    def export_backup_click(e):
        data_str = db.export_backup_json()
        page.set_clipboard(data_str)
        show_msg("Skopiowano backup bazy do schowka! Mozesz przeslac go na drugi telefon.")

    def import_backup_click(e):
        if not backup_json_tf.value.strip():
            show_msg("Wklej najpierw tekst backupu!", True)
            return
        try:
            db.import_backup_json(backup_json_tf.value.strip())
            backup_json_tf.value = ""
            refresh_diet()
            refresh_recipes_and_shopping()
            refresh_workouts()
            refresh_progress()
            show_msg("Zaimportowano dane pomyslnie!")
        except Exception as ex:
            show_msg(f"Blad importu: {ex}", True)

    def calc_bmr():
        try:
            age = int(profile_age.value or 24)
            height = float(profile_height.value or 163)
            weight = float(db.get_setting("current_weight", "90") or 90)
            gender = profile_gender.value
            bmr = (10 * weight + 6.25 * height - 5 * age + 5) if gender == "Mezczyzna" \
                  else (10 * weight + 6.25 * height - 5 * age - 161)
            activity_map = {"Siedzacy tryb zycia": 1.2, "Lekko aktywny": 1.375,
                "Umiarkowanie aktywny": 1.55, "Bardzo aktywny": 1.725, "Ekstremalnie aktywny": 1.9}
            tdee = round(bmr * activity_map.get(profile_activity.value, 1.55))
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
        db.set_setting("target_water", t_water_field.value.strip())
        calc_bmr()
        refresh_diet()
        refresh_progress()
        page.update()
        show_msg("Ustawienia zapisane!")

    settings_view = ft.Column([
        make_header("Profil i Ustawienia"),
        make_card(ft.Column([
            ft.Row([ft.Icon("key", color="#00E676", size=20),
                ft.Text("Konfiguracja AI", weight=ft.FontWeight.BOLD, size=15)], spacing=8),
            api_key_field, model_field,
            ft.Text("Zalecany model: gemini-2.5-flash | gemini-2.0-flash",
                size=11, color="#666666", italic=True),
        ])),
        make_card(ft.Column([
            ft.Row([ft.Icon("person", color="#42A5F5", size=20),
                ft.Text("Profil osoby", weight=ft.FontWeight.BOLD, size=15)], spacing=8),
            profile_name,
            ft.Row([profile_age, profile_height], spacing=10),
            profile_gender, profile_activity,
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
            t_weight_field, t_water_field,
        ])),
        ft.Container(padding=ft.padding.symmetric(horizontal=12, vertical=4),
            content=accent_btn("Zapisz ustawienia", "save", save_settings_click)),
        make_card(ft.Column([
            ft.Row([ft.Icon("sync_alt", color="#AB47BC", size=20),
                ft.Text("Przenoszenie danych miedzy telefonami", weight=ft.FontWeight.BOLD, size=15, color="#AB47BC")], spacing=8),
            ft.Text("Skopiuj cala baze (posilki, przepisy, treningi, szablony) i wklej na drugim telefonie:",
                size=12, color="#9E9E9E"),
            ft.ElevatedButton("Kopiuj Backup Bazy", icon="content_copy", bgcolor="#6A1B9A", color="white",
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), elevation=0),
                on_click=export_backup_click),
            backup_json_tf,
            ft.ElevatedButton("Importuj wklejony Backup", icon="download", bgcolor="#1565C0", color="white",
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), elevation=0),
                on_click=import_backup_click),
        ])),
    ], visible=False)

    # =========================================================================
    # NAWIGACJA – 6 ZAKLADEK (ZOPTYMALIZOWANE ETYKIETY + SAFEAREA)
    # =========================================================================
    views = [diet_view, recipes_view, workout_view, progress_view, chat_view, settings_view]

    def on_nav_change(e):
        idx = e.control.selected_index
        for i, v in enumerate(views):
            v.visible = (i == idx)
        if idx == 0: refresh_diet()
        elif idx == 1: refresh_recipes_and_shopping()
        elif idx == 2: refresh_workouts()
        elif idx == 3: refresh_progress()
        elif idx == 4: refresh_chat()
        page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0, on_change=on_nav_change,
        bgcolor="#0F0F18", indicator_color="#1A2A1A",
        destinations=[
            ft.NavigationBarDestination(icon="restaurant_outlined", selected_icon="restaurant", label="Dieta"),
            ft.NavigationBarDestination(icon="menu_book_outlined", selected_icon="menu_book", label="Przepisy"),
            ft.NavigationBarDestination(icon="fitness_center_outlined", selected_icon="fitness_center", label="Trening"),
            ft.NavigationBarDestination(icon="trending_up", label="Postepy"),
            ft.NavigationBarDestination(icon="chat_outlined", selected_icon="chat", label="AI Chat"),
            ft.NavigationBarDestination(icon="settings_outlined", selected_icon="settings", label="Opcje"),
        ])

    build_calendar()
    page.add(
        ft.SafeArea(
            content=ft.Column([loading_bar, *views], spacing=0),
            expand=True
        )
    )
    refresh_diet()


ft.app(target=main)
