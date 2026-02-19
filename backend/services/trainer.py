import os
import re
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from config import GAME_CONFIGS


class TrainerService:
    def __init__(self):
        self.models_dir = "/data/models"
        os.makedirs(self.models_dir, exist_ok=True)
        self.target_accuracy = float(os.environ.get("TRAIN_TARGET_ACCURACY", "0.95"))
        self.max_train_attempts = int(os.environ.get("TRAIN_MAX_ATTEMPTS", "12"))

    def _parse_numbers(self, raw_value: str):
        tokens = re.findall(r"\d+", str(raw_value or ""))
        return [int(token) for token in tokens]

    def _get_rules(self, game: str):
        base = {
            "primary_count": 5,
            "primary_min": 1,
            "primary_max": 99,
            "primary_unique": True,
            "bonus_count": 0,
            "bonus_min": 1,
            "bonus_max": 99,
            "bonus_keys": [],
            "embedded_bonus_in_winning_numbers": False,
        }
        configured = GAME_CONFIGS.get(game, {}) or {}
        merged = {**base, **configured}
        merged["bonus_keys"] = [str(k).lower() for k in (merged.get("bonus_keys") or [])]
        return merged

    def _clamp_primary(self, numbers, rules):
        valid = [
            int(n)
            for n in numbers
            if rules["primary_min"] <= int(n) <= rules["primary_max"]
        ]

        if not valid:
            return []

        if rules.get("primary_unique", True):
            seen = set()
            uniq = []
            for value in valid:
                if value not in seen:
                    seen.add(value)
                    uniq.append(value)
            valid = uniq

        if len(valid) < rules["primary_count"]:
            return []
        return valid[:rules["primary_count"]]

    def _extract_bonus_values(self, metadata, rules):
        bonus_count = int(rules.get("bonus_count", 0) or 0)
        if bonus_count <= 0:
            return []

        values = []
        bonus_min = int(rules.get("bonus_min", 1))
        bonus_max = int(rules.get("bonus_max", 99))

        for key, value in (metadata or {}).items():
            key_lower = str(key).lower()
            if key_lower in rules["bonus_keys"] or ("bonus" in key_lower and "winning" not in key_lower):
                parsed = self._parse_numbers(value)
                for item in parsed:
                    if bonus_min <= item <= bonus_max:
                        values.append(item)
                        if len(values) >= bonus_count:
                            return values[:bonus_count]
        return values[:bonus_count]

    def _extract_primary_candidate(self, metadata):
        winning_value = None

        for key, value in (metadata or {}).items():
            key_lower = str(key).lower()
            if "winning" in key_lower and "number" in key_lower:
                winning_value = value
                break

        if winning_value is None:
            for key, value in (metadata or {}).items():
                key_lower = str(key).lower()
                if "numbers" in key_lower or "result" in key_lower:
                    if "draw_number" in key_lower:
                        continue
                    winning_value = value
                    break

        return self._parse_numbers(winning_value)

    def _extract_record_sequence(self, metadata, game: str):
        rules = self._get_rules(game)
        winning_numbers = self._extract_primary_candidate(metadata)
        if not winning_numbers:
            return []

        primary_count = int(rules["primary_count"])
        bonus_count = int(rules.get("bonus_count", 0) or 0)

        embedded_bonus = []
        if rules.get("embedded_bonus_in_winning_numbers") and bonus_count > 0 and len(winning_numbers) >= primary_count + bonus_count:
            embedded_bonus = winning_numbers[primary_count:primary_count + bonus_count]
            winning_numbers = winning_numbers[:primary_count]

        primary_numbers = self._clamp_primary(winning_numbers, rules)
        if len(primary_numbers) != primary_count:
            return []

        bonus_numbers = self._extract_bonus_values(metadata, rules)
        if not bonus_numbers and embedded_bonus:
            bonus_min = int(rules.get("bonus_min", 1))
            bonus_max = int(rules.get("bonus_max", 99))
            bonus_numbers = [int(n) for n in embedded_bonus if bonus_min <= int(n) <= bonus_max][:bonus_count]

        if bonus_count > 0 and bonus_numbers:
            return primary_numbers + bonus_numbers[:bonus_count]
        return primary_numbers

    def _extract_winning_sequences(self, metadatas, game: str):
        sequences = []
        for meta in metadatas or []:
            if not isinstance(meta, dict):
                continue

            numbers = self._extract_record_sequence(meta, game)
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

    def _fit_and_score_model(self, X_train, y_train, X_val, y_val, y_full, attempt: int):
        model = RandomForestRegressor(
            n_estimators=min(80 + (attempt * 25), 500),
            random_state=42 + attempt,
            n_jobs=-1,
            max_depth=min(12 + attempt, 28),
            min_samples_split=2,
        )
        model.fit(X_train, y_train)

        predictions = model.predict(X_val)
        mae = float(mean_absolute_error(y_val, predictions))
        max_val = float(np.max(y_full)) if np.max(y_full) > 0 else 1.0
        accuracy = max(0.0, 1.0 - (mae / max_val))
        return model, mae, accuracy

    def _train_recursive(self, X_train, y_train, X_val, y_val, y_full, attempt: int = 1, best_result: dict | None = None):
        model, mae, accuracy = self._fit_and_score_model(X_train, y_train, X_val, y_val, y_full, attempt)

        current = {
            "model": model,
            "mae": mae,
            "accuracy": accuracy,
            "attempt": attempt,
        }

        if best_result is None or accuracy > best_result["accuracy"]:
            best_result = current

        if accuracy >= self.target_accuracy:
            return {
                **current,
                "reached_target": True,
                "attempts": attempt,
            }

        if attempt >= self.max_train_attempts:
            return {
                **best_result,
                "reached_target": False,
                "attempts": attempt,
            }

        return self._train_recursive(
            X_train,
            y_train,
            X_val,
            y_val,
            y_full,
            attempt=attempt + 1,
            best_result=best_result,
        )

    def train_model(self, game: str):
        from .chroma_client import chroma_client

        collection = chroma_client.client.get_collection(game)
        data = collection.get(limit=6000, include=["metadatas"])
        metadatas = data.get("metadatas") if data else None
        if not metadatas:
            return {"status": "error", "message": "No data found to train on."}

        sequences = self._extract_winning_sequences(metadatas, game)
        X, y, feature_len, output_len = self._build_supervised_dataset(sequences)
        if X is None or len(X) < 10:
            return {"status": "error", "message": "Not enough parsed winning-number sequences to train."}

        train_size = 0.33
        val_size = 0.67
        X_train, X_val, y_train, y_val = train_test_split(
            X,
            y,
            train_size=train_size,
            test_size=val_size,
            random_state=42,
        )

        train_result = self._train_recursive(X_train, y_train, X_val, y_val, y)
        model = train_result["model"]
        mae = float(train_result["mae"])
        accuracy = float(train_result["accuracy"])

        model_path = os.path.join(self.models_dir, f"{game}_model.joblib")
        artifact = {
            "model": model,
            "feature_len": feature_len,
            "output_len": output_len,
            "game": game,
            "rules": self._get_rules(game),
            "version": 1,
            "metrics": {
                "accuracy": accuracy,
                "mae": mae,
                "attempts": int(train_result.get("attempts", 1)),
                "reached_target": bool(train_result.get("reached_target", False)),
                "target_accuracy": self.target_accuracy,
                "train_size": train_size,
                "validation_size": val_size,
            },
        }

        previous_accuracy = None
        if os.path.exists(model_path):
            try:
                existing_artifact = joblib.load(model_path)
                metrics = (existing_artifact or {}).get("metrics") if isinstance(existing_artifact, dict) else None
                if isinstance(metrics, dict):
                    existing_accuracy = metrics.get("accuracy")
                    if existing_accuracy is not None:
                        previous_accuracy = float(existing_accuracy)
            except Exception:
                previous_accuracy = None

        if previous_accuracy is not None and accuracy < previous_accuracy:
            return {
                "status": "success",
                "message": (
                    f"Training completed for {game}, but previous model was retained to minimize regression "
                    f"(new accuracy={accuracy:.4f} < previous accuracy={previous_accuracy:.4f})."
                ),
                "accuracy": previous_accuracy,
                "new_accuracy": accuracy,
                "mae": mae,
                "model_path": model_path,
                "feature_len": feature_len,
                "output_len": output_len,
                "samples": int(len(X)),
                "target_accuracy": self.target_accuracy,
                "attempts": int(train_result.get("attempts", 1)),
                "reached_target": bool(train_result.get("reached_target", False)),
                "retained_previous_model": True,
                "train_size": train_size,
                "validation_size": val_size,
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
            "target_accuracy": self.target_accuracy,
            "attempts": int(train_result.get("attempts", 1)),
            "reached_target": bool(train_result.get("reached_target", False)),
            "retained_previous_model": False,
            "train_size": train_size,
            "validation_size": val_size,
        }


trainer_service = TrainerService()
