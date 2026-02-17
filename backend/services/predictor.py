import os
import re
import numpy as np
import joblib
from config import GAME_PREDICTION_FORMATS

class PredictorService:
    def __init__(self):
        self.models_dir = "/data/models"

    def _parse_numbers(self, raw_value):
        return [int(token) for token in re.findall(r"\d+", str(raw_value or ""))]

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

    def _clamp_number(self, value, minimum, maximum):
        parsed = int(np.round(value))
        return max(minimum, min(maximum, parsed))

    def _ensure_unique(self, values, minimum, maximum):
        used = set()
        unique_values = []
        span = (maximum - minimum) + 1

        for value in values:
            candidate = value
            for _ in range(span):
                if candidate not in used:
                    break
                candidate = minimum + ((candidate - minimum + 1) % span)
            used.add(candidate)
            unique_values.append(candidate)

        return unique_values

    def _format_prediction(self, game: str, raw_numbers):
        format_spec = GAME_PREDICTION_FORMATS.get(game, {})
        main_count = int(format_spec.get("main_count", len(raw_numbers) or 0))
        bonus_count = int(format_spec.get("bonus_count", 0))
        total_count = main_count + bonus_count

        normalized = list(raw_numbers or [])
        if len(normalized) < total_count:
            normalized.extend([0] * (total_count - len(normalized)))
        if total_count > 0:
            normalized = normalized[:total_count]

        main_min = int(format_spec.get("main_min", 0))
        main_max = int(format_spec.get("main_max", 99))
        bonus_min = int(format_spec.get("bonus_min", main_min))
        bonus_max = int(format_spec.get("bonus_max", main_max))

        main_values = [self._clamp_number(value, main_min, main_max) for value in normalized[:main_count]]
        if format_spec.get("unique_main", False):
            main_values = self._ensure_unique(main_values, main_min, main_max)
        if format_spec.get("sort_main", False):
            main_values = sorted(main_values)

        bonus_values = [
            self._clamp_number(value, bonus_min, bonus_max)
            for value in normalized[main_count:main_count + bonus_count]
        ]

        formatted = {
            "main_numbers": main_values,
            "bonus_numbers": bonus_values,
            "main_label": format_spec.get("main_label", "Numbers"),
            "bonus_label": format_spec.get("bonus_label", "Bonus"),
            "has_bonus": bonus_count > 0,
        }

        return formatted, main_values + bonus_values

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
        
        # Round to nearest integers
        predicted_numbers = [max(0, int(np.round(value))) for value in prediction]
        formatted_prediction, normalized_flat = self._format_prediction(game, predicted_numbers)
        
        return {
            "status": "success",
            "game": game,
            "predicted_numbers": normalized_flat,
            "formatted_prediction": formatted_prediction,
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
