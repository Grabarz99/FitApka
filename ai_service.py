import requests
import json
import base64


class AIService:
    def __init__(self, db):
        self.db = db

    def _call_gemini(self, prompt, image_path=None, json_mode=False, use_search=False):
        api_key = self.db.get_setting("api_key", "").strip()
        model = self.db.get_setting("model_name", "gemini-3.8-flash").strip()

        if not api_key:
            raise ValueError("Brak klucza API! Wklej swoj klucz w zakladce Ustawienia.")

        if not model:
            model = "gemini-3.8-flash"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        parts = [{"text": prompt}]

        if image_path:
            try:
                with open(image_path, "rb") as img_file:
                    b64_data = base64.b64encode(img_file.read()).decode("utf-8")
                ext = image_path.lower().split(".")[-1]
                mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
                mime_type = mime_map.get(ext, "image/jpeg")
                parts.append({"inline_data": {"mime_type": mime_type, "data": b64_data}})
            except Exception as e:
                raise ValueError(f"Blad odczytu zdjecia: {e}")

        payload = {"contents": [{"parts": parts}]}

        if json_mode and not use_search:
            payload["generationConfig"] = {"responseMimeType": "application/json"}

        if use_search:
            payload["tools"] = [{"google_search": {}}]

        try:
            resp = requests.post(url, json=payload, timeout=60)
        except requests.exceptions.Timeout:
            raise RuntimeError("Przekroczono czas oczekiwania (60s). Sprobuj ponownie.")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Brak polaczenia z internetem.")

        if resp.status_code == 404:
            raise RuntimeError(f"Model '{model}' niedostepny. Zmien model w Ustawieniach.")
        if resp.status_code in (401, 403):
            raise RuntimeError("Nieprawidlowy klucz API. Sprawdz klucz w Ustawieniach.")
        if resp.status_code == 429:
            raise RuntimeError("Przekroczono limit zapytan. Poczekaj i sprobuj ponownie.")
        if resp.status_code != 200:
            raise RuntimeError(f"Blad Gemini API ({resp.status_code}): {resp.text[:200]}")

        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise RuntimeError(f"Nieoczekiwana odpowiedz API: {str(data)[:200]}")

    def _clean_json(self, text):
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        return text

    def analyze_food(self, description="", image_path=None):
        prompt = (
            "Przeanalizuj posilek: '" + description + "'. "
            "Zwroc TYLKO czysty JSON bez markdown:\n"
            '{"name":"nazwa po polsku","kcal":500,"protein":35.0,"fat":15.0,"carbs":50.0,"fiber":5.0,"sugar":8.0,"sodium":400}'
        )
        res = self._call_gemini(prompt, image_path=image_path, json_mode=True)
        return json.loads(self._clean_json(res))

    def get_product_by_barcode(self, barcode, weight_grams=100):
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode.strip()}.json"
        try:
            resp = requests.get(url, timeout=15)
            data = resp.json()
        except Exception as e:
            raise ValueError(f"Blad polaczenia z baza produktow: {e}")

        if data.get("status") != 1:
            raise ValueError("Nie znaleziono produktu o tym kodzie kreskowym.")

        prod = data["product"]
        nutr = prod.get("nutriments", {})
        factor = float(weight_grams) / 100.0

        def sf(val):
            try:
                return float(val)
            except (TypeError, ValueError):
                return 0.0

        return {
            "name": f"{prod.get('product_name', 'Produkt')} ({int(weight_grams)}g)",
            "kcal": int(sf(nutr.get("energy-kcal_100g", 0)) * factor),
            "protein": round(sf(nutr.get("proteins_100g", 0)) * factor, 1),
            "fat": round(sf(nutr.get("fat_100g", 0)) * factor, 1),
            "carbs": round(sf(nutr.get("carbohydrates_100g", 0)) * factor, 1),
            "fiber": round(sf(nutr.get("fiber_100g", 0)) * factor, 1),
            "sugar": round(sf(nutr.get("sugars_100g", 0)) * factor, 1),
            "sodium": round(sf(nutr.get("sodium_100g", 0)) * factor * 1000, 0),
        }

    def search_recipes(self, query_criteria):
        prompt = (
            "Przygotuj 3 przepisy pasujace do: \"" + query_criteria + "\". "
            "Zwroc TYLKO tablice JSON bez markdown:\n"
            '[{"title":"nazwa","kcal":550,"protein":45.0,"fat":18.0,"carbs":50.0,"fiber":6.0,'
            '"ingredients":["200g kurczaka","100g ryzu"],"instructions":"Krok 1..."}]'
        )
        res = self._call_gemini(prompt, json_mode=True)
        return json.loads(self._clean_json(res))

    def generate_workout_plan(self, goal_desc, recent_workouts):
        if recent_workouts:
            history_str = "\n".join([
                f"- {w[0]}: [{w[1]}] {w[2]} | {w[3]}x{w[4]} ({w[5]}kg) | {w[6]} min"
                for w in recent_workouts
            ])
        else:
            history_str = "Brak historii treningow."

        prompt = (
            "Jestes trenerem silowym.\n"
            f"Uzytkownik: waga={self.db.get_setting('current_weight','?')}kg, "
            f"cel={self.db.get_setting('target_weight','?')}kg, "
            f"wzrost={self.db.get_setting('height','?')}cm, "
            f"wiek={self.db.get_setting('profile_age','?')}lat, "
            f"plec={self.db.get_setting('profile_gender','?')}, "
            f"aktywnosc={self.db.get_setting('profile_activity','?')}\n"
            f"Cel: \"{goal_desc}\"\n"
            f"Historia:\n{history_str}\n\n"
            "Napisz plan treningowy w Markdown z ciezarami, seriami, powtorzeniami i progresja."
        )
        return self._call_gemini(prompt, json_mode=False)
