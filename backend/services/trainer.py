import os
import re
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split


class TrainerService:
    def __init__(self):
        self.models_dir = "/data/models"
        os.makedirs(self.models_dir, exist_ok=True)

    def _parse_numbers(self, raw_value: str):
        tokens = re.findall(r"\d+", str(raw_value or ""))
        return [int(token) for token in tokens]

    def _extract_winning_sequences(self, metadatas):
        sequences = []
        for meta in metadatas or []:
            if not isinstance(meta, dict):
                continue

            winning_value = None
            for key, value in meta.items():
                key_lower = str(key).lower()
                if "winning" in key_lower and "number" in key_lower:
                    winning_value = value
                    break

            if winning_value is None:
                for key, value in meta.items():
                    key_lower = str(key).lower()
                    if "numbers" in key_lower or "result" in key_lower:
                        winning_value = value
                        break

            numbers = self._parse_numbers(winning_value)
            if numbers:
                sequences.append(numbers)

        return sequences

    def _build_supervised_dataset(self, sequences):
        if len(sequences) < 2:
            return None, None, 0, 0

        feature_len = max(len(seq) for seq in sequences[:-1])
        output_len = max(len(seq) for seq in sequences[1:])

        X = []
        y = []
        for index in range(1, len(sequences)):
            features = sequences[index - 1][:feature_len]
            target = sequences[index][:output_len]

            if len(features) < feature_len:
                features = features + [0] * (feature_len - len(features))
            if len(target) < output_len:
                target = target + [0] * (output_len - len(target))

            X.append(features)
            y.append(target)

        return np.array(X), np.array(y), feature_len, output_len

    def train_model(self, game: str):
        from .chroma_client import chroma_client

        collection = chroma_client.client.get_collection(game)
        data = collection.get(limit=6000, include=["metadatas"])
        metadatas = data.get("metadatas") if data else None
        if not metadatas:
            return {"status": "error", "message": "No data found to train on."}

        sequences = self._extract_winning_sequences(metadatas)
        X, y, feature_len, output_len = self._build_supervised_dataset(sequences)
        if X is None or len(X) < 10:
            return {"status": "error", "message": "Not enough parsed winning-number sequences to train."}

        test_size = 0.25 if len(X) >= 40 else 0.2
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=test_size, random_state=42)

        model = RandomForestRegressor(
            n_estimators=80,
            random_state=42,
            n_jobs=-1,
            max_depth=12,
            min_samples_split=2,
        )
        model.fit(X_train, y_train)

        predictions = model.predict(X_val)
        mae = float(mean_absolute_error(y_val, predictions))
        max_val = float(np.max(y)) if np.max(y) > 0 else 1.0
        accuracy = max(0.0, 1.0 - (mae / max_val))

        model_path = os.path.join(self.models_dir, f"{game}_model.joblib")
        artifact = {
            "model": model,
            "feature_len": feature_len,
            "output_len": output_len,
            "game": game,
            "version": 1,
        }

        temp_model_path = f"{model_path}.tmp"
        joblib.dump(artifact, temp_model_path, compress=3)
        if not os.path.exists(temp_model_path) or os.path.getsize(temp_model_path) <= 0:
            return {"status": "error", "message": f"Failed to persist model artifact for {game}."}
        os.replace(temp_model_path, model_path)

        return {
            "status": "success",
            "message": f"Trained {game} model",
            "accuracy": accuracy,
            "mae": mae,
            "model_path": model_path,
            "feature_len": feature_len,
            "output_len": output_len,
            "samples": int(len(X)),
        }


trainer_service = TrainerService()
