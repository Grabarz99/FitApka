import sqlite3
import json
import os
from datetime import datetime

class FitDatabase:
    def __init__(self, db_path="fit_app.db"):
        self.db_path = db_path
        self.init_db()

    def get_conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_db(self):
        with self.get_conn() as conn:
            c = conn.cursor()
            
            # 1. Ustawienia i profil użytkownika (API Key, model, cel kaloryczny, waga)
            c.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Domyślne ustawienia
            defaults = {
                "api_key": "",
                "model_name": "gemini-2.5-flash",
                "target_kcal": "2200",
                "target_protein": "160",
                "target_fat": "70",
                "target_carbs": "230",
                "current_weight": "90.0",
                "target_weight": "70.0",
                "height": "163"
            }
            for k, v in defaults.items():
                c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

            # 2. Dziennik posiłków (4 posiłki: Śniadanie, II Śniadanie, Obiad, Kolacja)
            c.execute('''
                CREATE TABLE IF NOT EXISTS meals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    meal_type TEXT,
                    name TEXT,
                    kcal INTEGER,
                    protein REAL,
                    fat REAL,
                    carbs REAL
                )
            ''')

            # 3. Zapisane przepisy z AI / Internetu
            c.execute('''
                CREATE TABLE IF NOT EXISTS recipes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    kcal INTEGER,
                    protein REAL,
                    fat REAL,
                    carbs REAL,
                    ingredients_json TEXT,
                    instructions TEXT
                )
            ''')

            # 4. Lista zakupów
            c.execute('''
                CREATE TABLE IF NOT EXISTS shopping_list (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item TEXT,
                    checked INTEGER DEFAULT 0
                )
            ''')

            # 5. Dziennik treningów (Siłownia + Inne aktywności)
            c.execute('''
                CREATE TABLE IF NOT EXISTS workouts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    activity_type TEXT, -- 'Siłownia' lub 'Inna aktywność'
                    name TEXT,          -- Nazwa ćwiczenia lub aktywności (np. Hokej, Bieganie)
                    sets INTEGER,
                    reps INTEGER,
                    weight_kg REAL,
                    duration_min INTEGER,
                    kcal_burned INTEGER,
                    notes TEXT
                )
            ''')

            # 6. Plany treningowe wygenerowane przez AI
            c.execute('''
                CREATE TABLE IF NOT EXISTS ai_workout_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT,
                    plan_name TEXT,
                    plan_text TEXT
                )
            ''')

            # 7. Historia wagi i postępów
            c.execute('''
                CREATE TABLE IF NOT EXISTS weight_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    weight REAL
                )
            ''')
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

    # --- POSIŁKI ---
    def add_meal(self, date_str, meal_type, name, kcal, protein, fat, carbs):
        with self.get_conn() as conn:
            conn.execute('''
                INSERT INTO meals (date, meal_type, name, kcal, protein, fat, carbs)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (date_str, meal_type, name, int(kcal), float(protein), float(fat), float(carbs)))
            conn.commit()

    def get_meals_by_date(self, date_str):
        with self.get_conn() as conn:
            return conn.execute('''
                SELECT id, meal_type, name, kcal, protein, fat, carbs
                FROM meals WHERE date = ?
            ''', (date_str,)).fetchall()

    def delete_meal(self, meal_id):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
            conn.commit()

    # --- PRZEPISY I LISTA ZAKUPÓW ---
    def save_recipe(self, title, kcal, protein, fat, carbs, ingredients_list, instructions):
        with self.get_conn() as conn:
            conn.execute('''
                INSERT INTO recipes (title, kcal, protein, fat, carbs, ingredients_json, instructions)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, int(kcal), float(protein), float(fat), float(carbs), json.dumps(ingredients_list, ensure_ascii=False), instructions))
            conn.commit()

    def get_recipes(self):
        with self.get_conn() as conn:
            rows = conn.execute("SELECT id, title, kcal, protein, fat, carbs, ingredients_json, instructions FROM recipes ORDER BY id DESC").fetchall()
            result = []
            for r in rows:
                result.append({
                    "id": r[0], "title": r[1], "kcal": r[2],
                    "protein": r[3], "fat": r[4], "carbs": r[5],
                    "ingredients": json.loads(r[6]), "instructions": r[7]
                })
            return result

    def add_shopping_items(self, items_list):
        with self.get_conn() as conn:
            for item in items_list:
                conn.execute("INSERT INTO shopping_list (item, checked) VALUES (?, 0)", (item,))
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

    # --- TRENINGI I WAGA ---
    def add_workout(self, date_str, activity_type, name, sets=0, reps=0, weight_kg=0.0, duration_min=0, kcal_burned=0, notes=""):
        with self.get_conn() as conn:
            conn.execute('''
                INSERT INTO workouts (date, activity_type, name, sets, reps, weight_kg, duration_min, kcal_burned, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (date_str, activity_type, name, int(sets), int(reps), float(weight_kg), int(duration_min), int(kcal_burned), notes))
            conn.commit()

    def get_workouts_by_date(self, date_str):
        with self.get_conn() as conn:
            return conn.execute('''
                SELECT id, activity_type, name, sets, reps, weight_kg, duration_min, kcal_burned, notes
                FROM workouts WHERE date = ? ORDER BY id DESC
            ''', (date_str,)).fetchall()

    def get_recent_workouts(self, limit=30):
        with self.get_conn() as conn:
            return conn.execute('''
                SELECT date, activity_type, name, sets, reps, weight_kg, duration_min, kcal_burned
                FROM workouts ORDER BY date DESC, id DESC LIMIT ?
            ''', (limit,)).fetchall()

    def save_ai_plan(self, plan_name, plan_text):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        with self.get_conn() as conn:
            conn.execute("INSERT INTO ai_workout_plans (created_at, plan_name, plan_text) VALUES (?, ?, ?)", (now, plan_name, plan_text))
            conn.commit()

    def get_ai_plans(self):
        with self.get_conn() as conn:
            return conn.execute("SELECT id, created_at, plan_name, plan_text FROM ai_workout_plans ORDER BY id DESC").fetchall()

    def add_weight_log(self, date_str, weight):
        with self.get_conn() as conn:
            conn.execute("INSERT INTO weight_logs (date, weight) VALUES (?, ?)", (date_str, float(weight)))
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('current_weight', ?)", (str(weight),))
            conn.commit()

    def get_weight_logs(self):
        with self.get_conn() as conn:
            return conn.execute("SELECT date, weight FROM weight_logs ORDER BY date ASC").fetchall()
