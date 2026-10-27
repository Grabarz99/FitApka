import requests
import json
import base64


class AIService:
    def __init__(self, db):
        self.db = db

    def _call_gemini(self, prompt, image_path=None, json_mode=False, use_search=False):
        api_key = self.db.get_setting("api_key", "").strip()
        

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        parts = [{"text": prompt}]

        if image_path:
            try:
                with open(image_path, "rb") as img_file:
                    b64_data = base64.b64encode(img_file.read()).decode("utf-8")
                # Wykryj typ MIME na podstawie rozszerzenia
                ext = image_path.lower().split(".")[-1]
                mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
                mime_type = mime_map.get(ext, "image/jpeg")
                parts.append({
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": b64_data
                    }
                })
            except Exception as e:
                raise ValueError(f"Błąd odczytu zdjęcia: {e}")

        payload = {
            "contents": [{"parts": parts}]
        }

        if json_mode and not use_search:
            payload["generationConfig"] = {"responseMimeType": "application/json"}

        if use_search:
            payload["tools"] = [{"google_search": {}}]

        try:
            resp = requests.post(url, json=payload, timeout=60)
        except requests.exceptions.Timeout:
            raise RuntimeError("Przekroczono czas oczekiwania na odpowiedź Gemini API (60s). Spróbuj ponownie.")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Brak połączenia z internetem. Sprawdź sieć i spróbuj ponownie.")

        if resp.status_code == 404:
            raise RuntimeError(
                f"Model '{model}' nie istnieje lub jest niedostępny.\n"
                "Zmień model na 'gemini-2.0-flash' w zakładce Ustawienia."
            )
        if resp.status_code == 401 or resp.status_code == 403:
            raise RuntimeError(
                "Nieprawidłowy klucz API lub brak uprawnień.\n"
                "Sprawdź klucz Gemini API w zakładce Ustawienia."
            )
        if resp.status_code == 429:
            raise RuntimeError(
                "Przekroczono limit zapytań do Gemini API.\n"
                "Poczekaj chwilę i spróbuj ponownie."
            )
        if resp.status_code != 200:
            raise RuntimeError(f"Błąd Gemini API ({resp.status_code}): {resp.text[:300]}")

        data = resp.json()
        try:
            text_out = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise RuntimeError(f"Nieoczekiwana odpowiedź API: {str(data)[:300]}")

        return text_out

    # 1. Wyliczanie kalorii z opisu lub zdjęcia talerza
    def analyze_food(self, description="", image_path=None):
        prompt = f"""
Przeanalizuj podany posiłek (opis: '{description}') i wylicz szacunkowe wartości odżywcze.
Zwróć wynik WYŁĄCZNIE jako czysty obiekt JSON (bez markdown, bez ```json):
{{
    "name": "Krótka nazwa posiłku po polsku",
    "kcal": 500,
    "protein": 35.0,
    "fat": 15.0,
    "carbs": 50.0,
    "fiber": 5.0,
    "sugar": 8.0,
    "sodium": 400
}}
Wartości liczbowe muszą być liczbami (nie stringami). Kcal jako integer, reszta jako float.
"""
        res = self._call_gemini(prompt, image_path=image_path, json_mode=True)
        # Wyczyść ewentualne znaczniki markdown
        clean = res.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)

    # 2. Pobieranie produktu po kodzie kreskowym (OpenFoodFacts)
    def get_product_by_barcode(self, barcode, weight_grams=100):
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode.strip()}.json"
        try:
            resp = requests.get(url, timeout=15)
            data = resp.json()
        except Exception as e:
            raise ValueError(f"Błąd połączenia z bazą produktów: {e}")

        if data.get("status") != 1:
            raise ValueError("Nie znaleziono produktu o tym kodzie kreskowym.")

        prod = data["product"]
        nutr = prod.get("nutriments", {})
        factor = float(weight_grams) / 100.0

        def safe_float(val, default=0.0):
            try:
                return float(val)
            except (TypeError, ValueError):
                return default

        return {
            "name": f"{prod.get('product_name', 'Produkt')} ({int(weight_grams)}g)",
            "kcal": int(safe_float(nutr.get("energy-kcal_100g", 0)) * factor),
            "protein": round(safe_float(nutr.get("proteins_100g", 0)) * factor, 1),
            "fat": round(safe_float(nutr.get("fat_100g", 0)) * factor, 1),
            "carbs": round(safe_float(nutr.get("carbohydrates_100g", 0)) * factor, 1),
            "fiber": round(safe_float(nutr.get("fiber_100g", 0)) * factor, 1),
            "sugar": round(safe_float(nutr.get("sugars_100g", 0)) * factor, 1),
            "sodium": round(safe_float(nutr.get("sodium_100g", 0)) * factor * 1000, 0),  # mg
        }

    # 3. Wyszukiwarka przepisów pod makro
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
        "fiber": 6.0,
        "ingredients": ["200g piersi z kurczaka", "100g ryżu basmati", "10g oliwy z oliwek"],
        "instructions": "Krok 1... Krok 2..."
    }}
]
"""
        res = self._call_gemini(prompt, json_mode=True)
        clean_res = res.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean_res)

    # 4. Generator planu treningowego i progresji ciężaru
    def generate_workout_plan(self, goal_desc, recent_workouts):
        history_str = "\n".join([
            f"- {w[0]}: [{w[1]}] {w[2]} | {w[3]}x{w[4]} ({w[5]}kg) | {w[6]} min"
            for w in recent_workouts
        ]) if recent_workouts else "Brak zapisanej historii – użytkownik dopiero zaczyna dziennik."

        prompt = f"""
Jesteś trenerem przygotowania motorycznego i siłowego.
Dane użytkownika:
- Waga: {self.db.get_setting('current_weight', '?')} kg
- Cel wagowy: {self.db.get_setting('target_weight', '?')} kg
- Wzrost: {self.db.get_setting('height', '?')} cm
- Wiek: {self.db.get_setting('profile_age', '?')} lat
- Płeć: {self.db.get_setting('profile_gender', '?')}
- Poziom aktywności: {self.db.get_setting('profile_activity', '?')}

Cel treningowy: "{goal_desc}"

Ostatnie treningi (do wyliczenia progresji):
{history_str}

Rozpisz konkretny, przejrzysty plan treningowy w formacie Markdown z:
- Sugerowanym ciężarem w kg
- Liczbą serii i powtórzeń
- Wskazówkami progresji na kolejny tydzień
- Uwzględnieniem wszystkich aktywności wymienionych przez użytkownika
"""
        return self._call_gemini(prompt, json_mode=False)
