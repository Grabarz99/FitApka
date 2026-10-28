import sqlite3
import json
import os
from datetime import datetime


class FitDatabase:
    def __init__(self, db_path="fit_app.db"):
        self.db_path = db_path
        self.init_db()
        self._migrate_model()

    def get_conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _migrate_model(self):
        old_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash"]
        current = self.get_setting("model_name", "")
        if current in old_models or current == "":
            self.set_setting("model_name", "gemini-3.8-flash")

    def init_db(self):
        with self.get_conn() as conn:
            c = conn.cursor()

            c.execute('''CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT)''')

            defaults = {
                "api_key": "", "model_name": "gemini-3.8-flash",
                "target_kcal": "2200", "target_protein": "160",
                "target_fat": "70", "target_carbs": "230",
                "current_weight": "90.0", "target_weight": "70.0",
                "height": "175", "profile_name": "", "profile_age": "25",
                "profile_gender": "Mezczyzna", "profile_activity": "Umiarkowanie aktywny",
                "target_water": "8",
            }
            for k, v in defaults.items():
                c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

            c.execute('''CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, meal_type TEXT, name TEXT,
                kcal INTEGER, protein REAL, fat REAL, carbs REAL)''')

            c.execute('''CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT, kcal INTEGER, protein REAL, fat REAL, carbs REAL,
                ingredients_json TEXT, instructions TEXT)''')

            c.execute('''CREATE TABLE IF NOT EXISTS shopping_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT, checked INTEGER DEFAULT 0)''')

            c.execute('''CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, activity_type TEXT, name TEXT,
                sets INTEGER, reps INTEGER, weight_kg REAL,
                duration_min INTEGER, kcal_burned INTEGER, notes TEXT)''')

            c.execute('''CREATE TABLE IF NOT EXISTS ai_workout_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT, plan_name TEXT, plan_text TEXT)''')

            c.execute('''CREATE TABLE IF NOT EXISTS weight_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, weight REAL)''')

            # Nowe tabele
            c.execute('''CREATE TABLE IF NOT EXISTS water_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, glasses INTEGER DEFAULT 0)''')

            c.execute('''CREATE TABLE IF NOT EXISTS workout_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, exercises_json TEXT,
                created_at TEXT)''')

            c.execute('''CREATE TABLE IF NOT EXISTS progress_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, photo_path TEXT, note TEXT)''')

            c.execute('''CREATE TABLE IF NOT EXISTS ai_chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT, role TEXT, message TEXT)''')

            conn.commit()

    # --- USTAWIENIA ---
    def get_setting(self, key, default=""):
        with self.get_conn() as conn:
            res = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return res[0] if res else default

    def set_setting(self, key, value):
        with self.get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            conn.commit()

    # --- POSILKI ---
    def add_meal(self, date_str, meal_type, name, kcal, protein, fat, carbs):
        with self.get_conn() as conn:
            conn.execute('''INSERT INTO meals (date, meal_type, name, kcal, protein, fat, carbs)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (date_str, meal_type, name, int(kcal), float(protein), float(fat), float(carbs)))
            conn.commit()

    def get_meals_by_date(self, date_str):
        with self.get_conn() as conn:
            return conn.execute('''SELECT id, meal_type, name, kcal, protein, fat, carbs
                FROM meals WHERE date = ?''', (date_str,)).fetchall()

    def delete_meal(self, meal_id):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
            conn.commit()

    def get_kcal_for_date(self, date_str):
        with self.get_conn() as conn:
            res = conn.execute("SELECT SUM(kcal) FROM meals WHERE date = ?", (date_str,)).fetchone()
            return int(res[0] or 0)

    # --- PRZEPISY ---
    def save_recipe(self, title, kcal, protein, fat, carbs, ingredients_list, instructions):
        with self.get_conn() as conn:
            conn.execute('''INSERT INTO recipes (title, kcal, protein, fat, carbs, ingredients_json, instructions)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (title, int(kcal), float(protein), float(fat), float(carbs),
                 json.dumps(ingredients_list, ensure_ascii=False), instructions))
            conn.commit()

    def get_recipes(self):
        with self.get_conn() as conn:
            rows = conn.execute("SELECT id, title, kcal, protein, fat, carbs, ingredients_json, instructions FROM recipes ORDER BY id DESC").fetchall()
            return [{"id": r[0], "title": r[1], "kcal": r[2], "protein": r[3],
                     "fat": r[4], "carbs": r[5], "ingredients": json.loads(r[6]), "instructions": r[7]}
                    for r in rows]

    def delete_recipe(self, recipe_id):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
            conn.commit()

    # --- LISTA ZAKUPOW ---
    def add_shopping_items(self, items_list):
        with self.get_conn() as conn:
            for item in items_list:
                if item and item.strip():
                    conn.execute("INSERT INTO shopping_list (item, checked) VALUES (?, 0)", (item.strip(),))
            conn.commit()

    def get_shopping_list(self):
        with self.get_conn() as conn:
            return conn.execute("SELECT id, item, checked FROM shopping_list ORDER BY checked ASC, id DESC").fetchall()

    def toggle_shopping_item(self, item_id, checked):
        with self.get_conn() as conn:
            conn.execute("UPDATE shopping_list SET checked = ? WHERE id = ?", (1 if checked else 0, item_id))
            conn.commit()

    def clear_shopping_list(self):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM shopping_list")
            conn.commit()

    # --- TRENINGI ---
    def add_workout(self, date_str, activity_type, name, sets=0, reps=0,
                    weight_kg=0.0, duration_min=0, kcal_burned=0, notes=""):
        with self.get_conn() as conn:
            conn.execute('''INSERT INTO workouts (date, activity_type, name, sets, reps,
                weight_kg, duration_min, kcal_burned, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (date_str, activity_type, name, int(sets or 0), int(reps or 0),
                 float(weight_kg or 0), int(duration_min or 0), int(kcal_burned or 0), notes))
            conn.commit()

    def get_workouts_by_date(self, date_str):
        with self.get_conn() as conn:
            return conn.execute('''SELECT id, activity_type, name, sets, reps, weight_kg,
                duration_min, kcal_burned, notes FROM workouts WHERE date = ? ORDER BY id DESC''',
                (date_str,)).fetchall()

    def get_recent_workouts(self, limit=30):
        with self.get_conn() as conn:
            return conn.execute('''SELECT date, activity_type, name, sets, reps, weight_kg,
                duration_min, kcal_burned FROM workouts ORDER BY date DESC, id DESC LIMIT ?''',
                (limit,)).fetchall()

    def get_exercise_history(self, exercise_name):
        with self.get_conn() as conn:
            return conn.execute('''SELECT date, sets, reps, weight_kg FROM workouts
                WHERE name LIKE ? ORDER BY date ASC LIMIT 20''',
                (f"%{exercise_name}%",)).fetchall()

    def save_ai_plan(self, plan_name, plan_text):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        with self.get_conn() as conn:
            conn.execute("INSERT INTO ai_workout_plans (created_at, plan_name, plan_text) VALUES (?, ?, ?)",
                (now, plan_name, plan_text))
            conn.commit()

    def get_ai_plans(self):
        with self.get_conn() as conn:
            return conn.execute("SELECT id, created_at, plan_name, plan_text FROM ai_workout_plans ORDER BY id DESC").fetchall()

    # --- SZABLONY TRENINGOW ---
    def save_workout_template(self, name, exercises):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        with self.get_conn() as conn:
            conn.execute("INSERT INTO workout_templates (name, exercises_json, created_at) VALUES (?, ?, ?)",
                (name, json.dumps(exercises, ensure_ascii=False), now))
            conn.commit()

    def get_workout_templates(self):
        with self.get_conn() as conn:
            rows = conn.execute("SELECT id, name, exercises_json, created_at FROM workout_templates ORDER BY id DESC").fetchall()
            return [{"id": r[0], "name": r[1], "exercises": json.loads(r[2]), "created_at": r[3]} for r in rows]

    def delete_workout_template(self, template_id):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM workout_templates WHERE id = ?", (template_id,))
            conn.commit()

    # --- WAGA I POSTEPY ---
    def add_weight_log(self, date_str, weight):
        with self.get_conn() as conn:
            conn.execute("INSERT INTO weight_logs (date, weight) VALUES (?, ?)", (date_str, float(weight)))
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('current_weight', ?)", (str(weight),))
            conn.commit()

    def get_weight_logs(self):
        with self.get_conn() as conn:
            return conn.execute("SELECT date, weight FROM weight_logs ORDER BY date ASC").fetchall()

    # --- ZDJECIA SYLWETKI ---
    def add_progress_photo(self, date_str, photo_path, note=""):
        with self.get_conn() as conn:
            conn.execute("INSERT INTO progress_photos (date, photo_path, note) VALUES (?, ?, ?)",
                (date_str, photo_path, note))
            conn.commit()

    def get_progress_photos(self):
        with self.get_conn() as conn:
            return conn.execute("SELECT id, date, photo_path, note FROM progress_photos ORDER BY date DESC").fetchall()

    def delete_progress_photo(self, photo_id):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM progress_photos WHERE id = ?", (photo_id,))
            conn.commit()

    # --- WODA ---
    def get_water_today(self, date_str):
        with self.get_conn() as conn:
            res = conn.execute("SELECT glasses FROM water_logs WHERE date = ?", (date_str,)).fetchone()
            return int(res[0]) if res else 0

    def set_water_today(self, date_str, glasses):
        with self.get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO water_logs (date, glasses) VALUES (?, ?)",
                (date_str, int(glasses)))
            conn.commit()

    def add_water_glass(self, date_str):
        current = self.get_water_today(date_str)
        self.set_water_today(date_str, current + 1)
        return current + 1

    def remove_water_glass(self, date_str):
        current = self.get_water_today(date_str)
        new_val = max(0, current - 1)
        self.set_water_today(date_str, new_val)
        return new_val

    # --- STREAK ---
    def get_streak(self):
        from datetime import timedelta
        target_kcal = int(self.get_setting("target_kcal", "2200") or 2200)
        streak = 0
        check_date = datetime.now().date()
        for _ in range(365):
            date_str = check_date.strftime("%Y-%m-%d")
            kcal = self.get_kcal_for_date(date_str)
            if kcal > 0 and kcal <= target_kcal * 1.1:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        return streak

    # --- AI CHAT ---
    def save_chat_message(self, role, message):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_conn() as conn:
            conn.execute("INSERT INTO ai_chat_history (created_at, role, message) VALUES (?, ?, ?)",
                (now, role, message))
            conn.commit()

    def get_chat_history(self, limit=50):
        with self.get_conn() as conn:
            return conn.execute("SELECT role, message, created_at FROM ai_chat_history ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()

    def clear_chat_history(self):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM ai_chat_history")
            conn.commit()
