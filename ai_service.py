import requests
import json
import base64


class AIService:
    def __init__(self, db):
        self.db = db

    def _call_gemini(self, prompt, image_path=None, json_mode=False):
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
                with open(image_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                ext = image_path.lower().split(".")[-1]
                mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                        "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
                parts.append({"inline_data": {"mime_type": mime, "data": b64}})
            except Exception as e:
                raise ValueError(f"Blad odczytu zdjecia: {e}")

        payload = {"contents": [{"parts": parts}]}
        if json_mode:
            payload["generationConfig"] = {"responseMimeType": "application/json"}

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

    # 1. Analiza jedzenia z opisu lub zdjecia
    def analyze_food(self, description="", image_path=None):
        prompt = (
            "Przeanalizuj posilek: '" + description + "'. "
            "Zwroc TYLKO czysty JSON bez markdown:\n"
            '{"name":"nazwa po polsku","kcal":500,"protein":35.0,"fat":15.0,"carbs":50.0,"fiber":5.0,"sugar":8.0,"sodium":400}'
        )
        res = self._call_gemini(prompt, image_path=image_path, json_mode=True)
        return json.loads(self._clean_json(res))

    # 2. Kod kreskowy
    def get_product_by_barcode(self, barcode, weight_grams=100):
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode.strip()}.json"
        try:
            resp = requests.get(url, timeout=15)
            data = resp.json()
        except Exception as e:
            raise ValueError(f"Blad polaczenia: {e}")
        if data.get("status") != 1:
            raise ValueError("Nie znaleziono produktu o tym kodzie kreskowym.")
        prod = data["product"]
        nutr = prod.get("nutriments", {})
        factor = float(weight_grams) / 100.0
        def sf(v):
            try: return float(v)
            except: return 0.0
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

    # 3. Przepisy
    def search_recipes(self, query_criteria):
        prompt = (
            "Przygotuj 3 przepisy pasujace do: \"" + query_criteria + "\". "
            "Zwroc TYLKO tablice JSON bez markdown:\n"
            '[{"title":"nazwa","kcal":550,"protein":45.0,"fat":18.0,"carbs":50.0,"fiber":6.0,'
            '"ingredients":["200g kurczaka","100g ryzu"],"instructions":"Krok 1..."}]'
        )
        res = self._call_gemini(prompt, json_mode=True)
        return json.loads(self._clean_json(res))

    # 4. Plan treningowy
    def generate_workout_plan(self, goal_desc, recent_workouts):
        history = "\n".join([
            f"- {w[0]}: [{w[1]}] {w[2]} | {w[3]}x{w[4]} ({w[5]}kg) | {w[6]} min"
            for w in recent_workouts
        ]) if recent_workouts else "Brak historii."
        prompt = (
            "Jestes trenerem silowym.\n"
            f"Uzytkownik: waga={self.db.get_setting('current_weight','?')}kg, "
            f"cel={self.db.get_setting('target_weight','?')}kg, "
            f"wzrost={self.db.get_setting('height','?')}cm, "
            f"wiek={self.db.get_setting('profile_age','?')}lat, "
            f"plec={self.db.get_setting('profile_gender','?')}, "
            f"aktywnosc={self.db.get_setting('profile_activity','?')}\n"
            f"Cel: \"{goal_desc}\"\nHistoria:\n{history}\n\n"
            "Napisz plan treningowy w Markdown z ciezarami, seriami, powtorzeniami i progresja."
        )
        return self._call_gemini(prompt)

    # 5. Chatbot dietetyczny
    def chat(self, user_message, chat_history):
        history_text = ""
        for role, msg, _ in reversed(list(chat_history)[:10]):
            prefix = "Uzytkownik" if role == "user" else "AI"
            history_text += f"{prefix}: {msg}\n"

        prompt = (
            "Jestes osobistym dietetykiem i trenerem fitness. Odpowiadaj po polsku, krotko i konkretnie.\n"
            f"Dane uzytkownika: waga={self.db.get_setting('current_weight','?')}kg, "
            f"cel={self.db.get_setting('target_weight','?')}kg, "
            f"wzrost={self.db.get_setting('height','?')}cm, "
            f"wiek={self.db.get_setting('profile_age','?')}lat, "
            f"plec={self.db.get_setting('profile_gender','?')}, "
            f"cel kaloryczny={self.db.get_setting('target_kcal','2200')}kcal\n\n"
            f"Historia rozmowy:\n{history_text}\n"
            f"Uzytkownik: {user_message}\n"
            "Odpowiedz:"
        )
        return self._call_gemini(prompt)

    # 6. Analiza diety
    def analyze_diet(self, meals_data):
        meals_text = "\n".join([
            f"- {m[1]}: {m[2]} | {m[3]}kcal B:{m[4]}g T:{m[5]}g W:{m[6]}g"
            for m in meals_data
        ]) if meals_data else "Brak posilkow."
        target_kcal = self.db.get_setting("target_kcal", "2200")
        target_p = self.db.get_setting("target_protein", "160")
        target_f = self.db.get_setting("target_fat", "70")
        target_c = self.db.get_setting("target_carbs", "230")
        prompt = (
            "Jestes dietetykiem. Przeanalizuj dzisiejsza diete uzytkownika.\n"
            f"Cele: {target_kcal}kcal, B:{target_p}g, T:{target_f}g, W:{target_c}g\n"
            f"Zjedzone dzisiaj:\n{meals_text}\n\n"
            "Oceń diete w punktach:\n"
            "1. Czy cele sa osiagniete?\n"
            "2. Co jest dobrze?\n"
            "3. Co poprawic?\n"
            "4. Propozycja na resztę dnia\n"
            "Odpowiedz krotko po polsku, max 200 slow."
        )
        return self._call_gemini(prompt)

    # 7. Codzienna motywacja i porada
    def get_daily_motivation(self):
        streak = self.db.get_streak()
        weight = self.db.get_setting("current_weight", "?")
        target = self.db.get_setting("target_weight", "?")
        prompt = (
            "Jestes motywujacym trenerem personalnym. "
            f"Uzytkownik ma streak {streak} dni, waze {weight}kg, cel {target}kg. "
            "Napisz krotka (2-3 zdania) motywujaca wiadomosc na dzis po polsku. "
            "Dodaj 1 konkretna porade treningowa lub dietetyczna na dzis."
        )
        return self._call_gemini(prompt)

    # 8. Kalkulator 1RM
    def calculate_1rm(self, weight_kg, reps):
        rm = round(float(weight_kg) * (1 + float(reps) / 30), 1)
        return rm

    # 9. Analiza zdjecia sylwetki
    def analyze_progress_photo(self, image_path):
        prompt = (
            "Jestes trenerem personalnym. Przeanalizuj zdjecie sylwetki uzytkownika. "
            "Opisz krotko (3-4 zdania) widoczne postepy, mocne strony i obszary do poprawy. "
            "Odpowiedz po polsku, motywujaco."
        )
        return self._call_gemini(prompt, image_path=image_path)
