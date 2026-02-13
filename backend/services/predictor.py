import os
import re
import numpy as np
import joblib

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
        
        return {
            "status": "success",
            "game": game,
            "predicted_numbers": predicted_numbers,
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
