import requests
import json
import base64

class AIService:
    def __init__(self, db):
        self.db = db

    def _call_gemini(self, prompt, image_path=None, json_mode=False, use_search=False):
        api_key = self.db.get_setting("api_key").strip()
        model = self.db.get_setting("model_name", "gemini-2.5-flash").strip()

        if not api_key:
            raise ValueError("Brak klucza API! Wklej swój klucz w zakładce Ustawienia.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        parts = [{"text": prompt}]
        
        # Obsługa zdjęcia jedzenia (jeśli podano)
        if image_path:
            with open(image_path, "rb") as img_file:
                b64_data = base64.b64encode(img_file.read()).decode("utf-8")
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": b64_data
                }
            })

        payload = {
            "contents": [{"parts": parts}]
        }

        if json_mode and not use_search:
            payload["generationConfig"] = {"responseMimeType": "application/json"}
        
        if use_search:
            payload["tools"] = [{"google_search": {}}]

        resp = requests.post(url, json=payload, timeout=45)
        if resp.status_code != 200:
            raise RuntimeError(f"Błąd Gemini API ({resp.status_code}): {resp.text}")

        data = resp.json()
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
        return text_out

    # 1. Wyliczanie kalorii z opisu lub zdjęcia talerza
    def analyze_food(self, description="", image_path=None):
        prompt = f"""
        Przeanalizuj podany posiłek (opis: '{description}') i wylicz szacunkowe wartości odżywcze.
        Zwróć wynik WYŁĄCZNIE jako czysty obiekt JSON w formacie:
        {{
            "name": "Krótka nazwa posiłku po polsku",
            "kcal": 500,
            "protein": 35.0,
            "fat": 15.0,
            "carbs": 50.0
        }}
        """
        res = self._call_gemini(prompt, image_path=image_path, json_mode=True)
        return json.loads(res)

    # 2. Pobieranie produktu po kodzie kreskowym (OpenFoodFacts)
    def get_product_by_barcode(self, barcode, weight_grams=100):
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode.strip()}.json"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        if data.get("status") != 1:
            raise ValueError("Nie znaleziono produktu o tym kodzie kreskowym.")
        
        prod = data["product"]
        nutr = prod.get("nutriments", {})
        factor = float(weight_grams) / 100.0
        
        return {
            "name": f"{prod.get('product_name', 'Produkt')} ({int(weight_grams)}g)",
            "kcal": int(float(nutr.get("energy-kcal_100g", 0)) * factor),
            "protein": round(float(nutr.get("proteins_100g", 0)) * factor, 1),
            "fat": round(float(nutr.get("fat_100g", 0)) * factor, 1),
            "carbs": round(float(nutr.get("carbohydrates_100g", 0)) * factor, 1)
        }

    # 3. Wyszukiwarka przepisów z internetu pod makro (Opcja B)
    def search_recipes(self, query_criteria):
        prompt = f"""
        Wyszukaj i przygotuj 3 konkretne, smaczne przepisy pasujące do kryteriów: "{query_criteria}".
        Zwróć odpowiedź WYŁĄCZNIE jako tablicę JSON (bez znaczników markdown ```json):
        [
            {{
                "title": "Nazwa dania",
                "kcal": 550,
                "protein": 45.0,
                "fat": 18.0,
                "carbs": 50.0,
                "ingredients": ["200g piersi z kurczaka", "100g ryżu basmati", "10g oliwy z oliwek"],
                "instructions": "Krok 1... Krok 2..."
            }}
        ]
        """
        res = self._call_gemini(prompt, json_mode=True)
        clean_res = res.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(clean_res)

    # 4. Generator planu treningowego i progresji ciężaru
    def generate_workout_plan(self, goal_desc, recent_workouts):
        history_str = "\n".join([
            f"- {w[0]}: [{w[1]}] {w[2]} | {w[3]}x{w[4]} ({w[5]}kg) | {w[6]} min"
            for w in recent_workouts
        ]) if recent_workouts else "Brak zapisanej historii – użytkownik dopiero zaczyna dziennik."

        prompt = f"""
        Jesteś trenerem przygotowania motorycznego i siłowego.
        Dane użytkownika: Waga: {self.db.get_setting('current_weight')} kg, Cel wagowy: {self.db.get_setting('target_weight')} kg, Wzrost: {self.db.get_setting('height')} cm.
        Cel treningowy / prośba użytkownika: "{goal_desc}"
        
        Ostatnie treningi użytkownika (do wyliczenia progresji):
        {history_str}

        Rozpisz konkretny, przejrzysty plan treningowy (wraz z sugerowanym ciężarem w kg, liczbą serii, powtórzeń oraz wskazówkami progresji na kolejny tydzień). Uwzględnij zarówno siłownię, jak i inne aktywności, o których wspomina użytkownik.
        """
        return self._call_gemini(prompt, json_mode=False)
