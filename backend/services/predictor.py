import os
import re
import numpy as np
import joblib
from config import GAME_CONFIGS

class PredictorService:
    def __init__(self):
        self.models_dir = "/data/models"

    def _parse_numbers(self, raw_value):
        return [int(token) for token in re.findall(r"\d+", str(raw_value or ""))]

    def _get_rules(self, game: str):
        base = {
            "primary_count": 5,
            "primary_min": 1,
            "primary_max": 99,
            "primary_unique": True,
            "bonus_count": 0,
            "bonus_min": 1,
            "bonus_max": 99,
        }
        configured = GAME_CONFIGS.get(game, {}) or {}
        return {**base, **configured}

    def _normalize_primary_predictions(self, values, rules):
        primary_count = int(rules["primary_count"])
        primary_min = int(rules["primary_min"])
        primary_max = int(rules["primary_max"])
        unique_required = bool(rules.get("primary_unique", True))

        normalized = []
        for value in values[:primary_count]:
            n = int(np.round(value))
            n = max(primary_min, min(primary_max, n))
            if unique_required and n in normalized:
                candidate = n
                while candidate in normalized and candidate <= primary_max:
                    candidate += 1
                while candidate in normalized and candidate >= primary_min:
                    candidate -= 1
                n = max(primary_min, min(primary_max, candidate))
            normalized.append(n)

        if unique_required:
            seen = set()
            deduped = []
            for n in normalized:
                if n not in seen:
                    seen.add(n)
                    deduped.append(n)
            normalized = deduped

            candidate = primary_min
            while len(normalized) < primary_count and candidate <= primary_max:
                if candidate not in seen:
                    seen.add(candidate)
                    normalized.append(candidate)
                candidate += 1

        while len(normalized) < primary_count:
            normalized.append(primary_min)

        return normalized[:primary_count]

    def _normalize_bonus_predictions(self, values, rules, include_bonus):
        if not include_bonus:
            return []

        bonus_count = int(rules.get("bonus_count", 0) or 0)
        bonus_min = int(rules.get("bonus_min", 1))
        bonus_max = int(rules.get("bonus_max", 99))

        normalized = []
        for value in values[:bonus_count]:
            n = int(np.round(value))
            n = max(bonus_min, min(bonus_max, n))
            normalized.append(n)

        while len(normalized) < bonus_count:
            normalized.append(bonus_min)

        return normalized[:bonus_count]

    def _extract_sequence(self, metadata):
        if not isinstance(metadata, dict):
            return []

        winning_value = None
        for key, value in metadata.items():
            key_lower = str(key).lower()
            if "winning" in key_lower and "number" in key_lower:
                winning_value = value
                break

        if winning_value is None:
            for key, value in metadata.items():
                key_lower = str(key).lower()
                if "numbers" in key_lower or "result" in key_lower:
                    winning_value = value
                    break

        return self._parse_numbers(winning_value)

    def predict_next_draw(self, game: str, recent_k: int = 10):
        # Lazy import to avoid ChromaDB connection during module import
        from .chroma_client import chroma_client
        
        model_path = os.path.join(self.models_dir, f"{game}_model.joblib")
        if not os.path.exists(model_path):
            return {"status": "error", "message": f"Model for game '{game}' not found."}
        if os.path.getsize(model_path) <= 0:
            return {"status": "error", "message": f"Model for game '{game}' is empty/corrupted."}

        try:
            artifact = joblib.load(model_path)
        except Exception as exc:
            return {"status": "error", "message": f"Unable to load model for game '{game}': {str(exc)}"}
        model = artifact.get("model")
        feature_len = int(artifact.get("feature_len", 10))
        output_len = int(artifact.get("output_len", 6))
        rules = artifact.get("rules") or self._get_rules(game)
        if model is None:
            return {"status": "error", "message": f"Model artifact for game '{game}' is invalid."}

        # Fetch recent draws from ChromaDB for prediction input
        collection = chroma_client.client.get_collection(game)
        data = collection.get(limit=recent_k, include=["metadatas"])  # Get recent entries
        
        if not data or not data['metadatas']:
             return {"status": "error", "message": "Not enough data to make a prediction."}
        
        sequences = [self._extract_sequence(meta) for meta in data['metadatas']]
        sequences = [seq for seq in sequences if seq]
        
        if not sequences:
            return {"status": "error", "message": "No valid sequences found."}
        
        # Use the most recent sequence
        seq = sequences[0]
        seq = seq + [0] * (feature_len - len(seq)) if len(seq) < feature_len else seq[:feature_len]
        
        X = np.array([seq])
        
        prediction = model.predict(X)
        prediction = np.array(prediction).reshape(-1)[:output_len]

        primary_count = int(rules.get("primary_count", 5))
        bonus_count = int(rules.get("bonus_count", 0) or 0)
        include_bonus = bonus_count > 0 and output_len >= (primary_count + bonus_count)

        primary_raw = prediction[:primary_count]
        bonus_raw = prediction[primary_count:primary_count + bonus_count] if include_bonus else []

        primary_numbers = self._normalize_primary_predictions(primary_raw, rules)
        bonus_numbers = self._normalize_bonus_predictions(bonus_raw, rules, include_bonus)
        predicted_numbers = primary_numbers + bonus_numbers
        
        return {
            "status": "success",
            "game": game,
            "predicted_numbers": predicted_numbers,
            "predicted_main_numbers": primary_numbers,
            "predicted_bonus_numbers": bonus_numbers,
        }

    def predict_all_games(self, games, recent_k: int = 10):
        results = {}
        for game in games:
            try:
                results[game] = self.predict_next_draw(game, recent_k)
            except Exception as exc:
                results[game] = {"error": str(exc)}
        return results

# Export a module-level instance expected by main_rag and other modules
predictor_service = PredictorService()
