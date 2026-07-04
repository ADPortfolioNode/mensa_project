import json
import os
import re
import time
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from config import GAME_CONFIGS


class TrainerService:
    def __init__(self):
        self.models_dir = "/data/models"
        os.makedirs(self.models_dir, exist_ok=True)
        defaults = self.get_training_defaults()
        self.target_accuracy = float(os.environ.get("TRAIN_TARGET_ACCURACY", defaults["target_accuracy"]))
        self.max_train_attempts = int(os.environ.get("TRAIN_MAX_ATTEMPTS", defaults["max_iterations"]))
        self.blend_step = float(os.environ.get("TRAIN_BLEND_STEP", defaults["blend_step"]))
        self.train_size = float(os.environ.get("TRAIN_SIZE", defaults["train_size"]))
        self.n_estimators = int(os.environ.get("TRAIN_N_ESTIMATORS", defaults["n_estimators"]))
        self.max_depth = int(os.environ.get("TRAIN_MAX_DEPTH", defaults["max_depth"]))
        self.random_state = int(os.environ.get("TRAIN_RANDOM_STATE", defaults["random_state"]))
        self.data_limit = int(os.environ.get("TRAIN_DATA_LIMIT", defaults["data_limit"]))
        self.window_size = int(os.environ.get("TRAIN_WINDOW_SIZE", defaults["window_size"]))
        self.auto_tune = str(os.environ.get("TRAIN_AUTO_TUNE", "1")).lower() not in ("0", "false", "no")

    @staticmethod
    def get_training_defaults():
        return {
            "target_accuracy": 0.90,
            "max_iterations": 40,
            "train_size": 0.25,
            "n_estimators": 250,
            "max_depth": 18,
            "random_state": 42,
            "blend_step": 0.05,
            "data_limit": 0,
            "window_size": 3,
            "auto_tune": True,
        }

    def configure_training(
        self,
        *,
        target_accuracy=None,
        max_iterations=None,
        train_size=None,
        n_estimators=None,
        max_depth=None,
        random_state=None,
        blend_step=None,
        data_limit=None,
        window_size=None,
        auto_tune=None,
    ):
        if target_accuracy is not None:
            self.target_accuracy = float(target_accuracy)
        if max_iterations is not None:
            self.max_train_attempts = int(max_iterations)
        if train_size is not None:
            self.train_size = float(train_size)
        if n_estimators is not None:
            self.n_estimators = int(n_estimators)
        if max_depth is not None:
            self.max_depth = int(max_depth)
        if random_state is not None:
            self.random_state = int(random_state)
        if blend_step is not None:
            self.blend_step = float(blend_step)
        if data_limit is not None:
            self.data_limit = int(data_limit)
        if window_size is not None:
            self.window_size = max(1, int(window_size))
        if auto_tune is not None:
            self.auto_tune = bool(auto_tune)

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
        preferred = []
        fallback = []

        for key, value in (metadata or {}).items():
            key_lower = str(key).lower()
            if "draw_number" in key_lower or not str(value or "").strip():
                continue

            if key_lower in ("winning_numbers", "winningnumbers"):
                preferred.append(value)
            elif "winning" in key_lower and "number" in key_lower:
                fallback.append(value)
            elif "numbers" in key_lower or "result" in key_lower:
                fallback.append(value)

        for candidate in preferred + fallback:
            numbers = self._parse_numbers(candidate)
            if numbers:
                return numbers

        return []

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

    def _metadata_sort_key(self, metadata):
        if not isinstance(metadata, dict):
            return ""
        for key in ("draw_date", "drawdate", "date", "drawn_at", "draw_datetime"):
            for variant in (key, key.upper(), key.title()):
                value = metadata.get(variant)
                if value:
                    return str(value)
        return ""

    def _sort_metadatas_chronologically(self, metadatas):
        if not metadatas:
            return []
        return sorted(metadatas, key=self._metadata_sort_key)

    def _load_all_metadatas(self, collection):
        page_size = 5000
        total = int(collection.count() or 0)
        if total <= 0:
            return []

        if self.data_limit and self.data_limit > 0:
            total = min(total, self.data_limit)

        metadatas = []
        offset = 0
        while offset < total:
            batch_size = min(page_size, total - offset)
            data = collection.get(
                limit=batch_size,
                offset=offset,
                include=["metadatas"],
            )
            batch = data.get("metadatas") if data else None
            if not batch:
                break
            metadatas.extend(batch)
            offset += len(batch)
            if len(batch) < batch_size:
                break
        return metadatas

    def _extract_winning_sequences(self, metadatas, game: str):
        sequences = []
        for meta in metadatas or []:
            if not isinstance(meta, dict):
                continue

            numbers = self._extract_record_sequence(meta, game)
            if numbers:
                sequences.append(numbers)

        return sequences

    def _build_supervised_dataset(self, sequences, window_size: int | None = None):
        window = max(1, int(window_size or self.window_size or 1))
        if len(sequences) < window + 1:
            return None, None, 0, 0

        output_len = max(len(seq) for seq in sequences)
        feature_len = output_len * window

        X = []
        y = []
        for index in range(window, len(sequences)):
            features = []
            for seq in sequences[index - window:index]:
                padded = list(seq[:output_len]) + [0] * max(0, output_len - len(seq))
                features.extend(padded[:output_len])
            target = list(sequences[index][:output_len]) + [0] * max(0, output_len - len(sequences[index]))
            X.append(features[:feature_len])
            y.append(target[:output_len])

        return np.array(X), np.array(y), feature_len, output_len

    @staticmethod
    def build_feature_vector(sequences, window_size: int, feature_len: int):
        window = max(1, int(window_size or 1))
        usable = [seq for seq in (sequences or []) if seq]
        if not usable:
            return []

        per_draw = max(1, feature_len // window)
        recent = usable[-window:]
        if len(recent) < window:
            recent = ([[]] * (window - len(recent))) + recent

        features = []
        for seq in recent:
            padded = list(seq[:per_draw]) + [0] * max(0, per_draw - len(seq))
            features.extend(padded[:per_draw])
        return features[:feature_len]

    def _chronological_split(self, X, y, train_size: float):
        split_idx = int(len(X) * float(train_size))
        split_idx = max(10, min(split_idx, len(X) - 10))
        return X[:split_idx], X[split_idx:], y[:split_idx], y[split_idx:]

    def _score_predictions(self, y_true, y_pred, y_full):
        max_val = float(np.max(y_full)) if np.max(y_full) > 0 else 1.0
        y_pred_scored = np.rint(np.asarray(y_pred, dtype=float))
        y_pred_scored = np.clip(y_pred_scored, 0, max_val)
        mae = float(mean_absolute_error(y_true, y_pred_scored))
        accuracy = max(0.0, 1.0 - (mae / max_val))
        return mae, accuracy

    def _train_size_candidates(self):
        if not self.auto_tune:
            return [float(self.train_size or 0.25)]
        preferred = float(self.train_size or 0.25)
        return sorted({round(preferred, 4), 0.22, 0.25, 0.33})

    def _select_best_candidate(self, candidates, y_val, y_full):
        if not candidates:
            return None

        best_single = max(candidates, key=lambda item: float(item.get("accuracy", 0.0)))
        ensemble_candidate = self._build_top3_ensemble(candidates, y_val, y_full)

        if (
            ensemble_candidate is not None
            and float(ensemble_candidate["accuracy"]) > float(best_single["accuracy"])
        ):
            return {
                "strategy": ensemble_candidate["strategy"],
                "model": ensemble_candidate["model"],
                "top_models": ensemble_candidate.get("top_models"),
                "ensemble_weights": ensemble_candidate.get("ensemble_weights"),
                "top_k_accuracies": ensemble_candidate.get("top_k_accuracies"),
                "mae": float(ensemble_candidate["mae"]),
                "accuracy": float(ensemble_candidate["accuracy"]),
                "predictions": np.asarray(ensemble_candidate.get("predictions"), dtype=float),
                "candidate_accuracy": float(best_single["accuracy"]),
            }

        return {
            "strategy": "single",
            "model": best_single["model"],
            "top_models": None,
            "ensemble_weights": None,
            "top_k_accuracies": None,
            "mae": float(best_single["mae"]),
            "accuracy": float(best_single["accuracy"]),
            "predictions": np.asarray(best_single.get("predictions"), dtype=float),
            "candidate_accuracy": float(best_single["accuracy"]),
        }

    def _rf_n_jobs(self, sample_count: int, n_estimators: int) -> int:
        """Limit parallelism on large fits to reduce backend OOM risk (502 crashes)."""
        if sample_count >= 3000 or n_estimators >= 450:
            return 1
        if sample_count >= 1500 or n_estimators >= 300:
            return 2
        return -1

    def _fit_and_score_model(self, X_train, y_train, X_val, y_val, y_full, attempt: int):
        base_estimators = max(50, int(self.n_estimators or 250))
        base_depth = max(4, int(self.max_depth or 18))
        n_estimators = min(base_estimators + ((attempt - 1) * 20), 600)
        max_depth = min(base_depth + max(0, attempt - 1), 32)
        n_jobs = self._rf_n_jobs(len(X_train), n_estimators)
        model = RandomForestRegressor(
            n_estimators=n_estimators,
            random_state=int(self.random_state or 42) + attempt,
            n_jobs=n_jobs,
            max_depth=max_depth,
            min_samples_split=max(2, 4 - (attempt // 6)),
            min_samples_leaf=1,
        )
        model.fit(X_train, y_train)

        predictions = model.predict(X_val)
        mae, accuracy = self._score_predictions(y_val, predictions, y_full)
        return model, mae, accuracy, predictions

    def _ensemble_predictions(self, models, weights, X):
        if not models:
            raise ValueError("No models available for ensemble prediction")
        if len(models) == 1:
            return np.asarray(models[0].predict(X), dtype=float)

        weight_arr = np.asarray(weights[: len(models)], dtype=float)
        if weight_arr.sum() <= 0:
            weight_arr = np.ones(len(models), dtype=float)
        weight_arr = weight_arr / weight_arr.sum()

        stacked = np.stack(
            [np.asarray(model.predict(X), dtype=float) for model in models],
            axis=0,
        )
        return np.tensordot(weight_arr, stacked, axes=(0, 0))

    def _predict_with_artifact(self, artifact: dict, X):
        model_strategy = str((artifact or {}).get("model_strategy", "single"))
        primary_model = (artifact or {}).get("model")
        if primary_model is None:
            raise ValueError("Model artifact is missing primary model")

        if model_strategy == "ensemble_top3":
            top_models = (artifact or {}).get("top_models") or []
            ensemble_weights = (artifact or {}).get("ensemble_weights") or []
            usable_models = [model for model in top_models if model is not None]
            if len(usable_models) >= 2:
                return self._ensemble_predictions(usable_models, ensemble_weights, X)

        if model_strategy == "ensemble":
            secondary_model = (artifact or {}).get("secondary_model")
            if secondary_model is None:
                raise ValueError("Ensemble artifact is missing secondary model")
            blend_weight = float((artifact or {}).get("blend_weight", 0.7))
            blend_weight = max(0.0, min(1.0, blend_weight))
            primary_pred = np.asarray(primary_model.predict(X), dtype=float)
            secondary_pred = np.asarray(secondary_model.predict(X), dtype=float)
            return (blend_weight * primary_pred) + ((1.0 - blend_weight) * secondary_pred)

        return np.asarray(primary_model.predict(X), dtype=float)

    def _train_iterative_collect(self, X_train, y_train, X_val, y_val, y_full):
        candidates = []
        for attempt in range(1, max(1, int(self.max_train_attempts)) + 1):
            try:
                model, mae, accuracy, predictions = self._fit_and_score_model(
                    X_train, y_train, X_val, y_val, y_full, attempt
                )
                candidates.append(
                    {
                        "model": model,
                        "mae": float(mae),
                        "accuracy": float(accuracy),
                        "attempt": int(attempt),
                        "predictions": np.asarray(predictions, dtype=float),
                    }
                )
            except Exception:
                continue
        return candidates

    def _build_top3_ensemble(self, candidates, y_val, y_full):
        if len(candidates) < 2:
            return None

        top_k = sorted(candidates, key=lambda item: float(item.get("accuracy", 0.0)), reverse=True)[:3]
        accuracies = np.array([max(0.0, float(item.get("accuracy", 0.0))) for item in top_k], dtype=float)
        if accuracies.sum() <= 0:
            weights = np.ones(len(top_k), dtype=float) / len(top_k)
        else:
            weights = accuracies / accuracies.sum()

        stacked_preds = np.stack([item["predictions"] for item in top_k], axis=0)
        ensemble_preds = np.tensordot(weights, stacked_preds, axes=(0, 0))
        ensemble_mae, ensemble_accuracy = self._score_predictions(y_val, ensemble_preds, y_full)
        return {
            "strategy": "ensemble_top3",
            "model": top_k[0]["model"],
            "top_models": [item["model"] for item in top_k],
            "ensemble_weights": weights.tolist(),
            "mae": float(ensemble_mae),
            "accuracy": float(ensemble_accuracy),
            "predictions": ensemble_preds,
            "top_k_accuracies": [float(item.get("accuracy", 0.0)) for item in top_k],
            "attempts": len(candidates),
        }

    def _baseline_accuracy(self, artifact: dict | None, live_accuracy: float | None) -> float | None:
        """Return the highest known accuracy for the current saved model."""
        stored = None
        if isinstance(artifact, dict):
            metrics = artifact.get("metrics") or {}
            stored = metrics.get("accuracy")
            if stored is None:
                stored = artifact.get("accuracy")

        values = []
        if stored is not None:
            try:
                values.append(float(stored))
            except (TypeError, ValueError):
                pass
        if live_accuracy is not None:
            try:
                values.append(float(live_accuracy))
            except (TypeError, ValueError):
                pass

        return max(values) if values else None

    def _load_stored_baseline(self, game: str) -> float | None:
        """Load highest known accuracy from persisted metadata JSON."""
        experiments_dir = os.path.join(os.path.dirname(self.models_dir), "experiments")
        metadata_path = os.path.join(experiments_dir, f"{game}_model_metadata.json")
        if not os.path.exists(metadata_path):
            return None

        try:
            with open(metadata_path, "r") as handle:
                data = json.load(handle)
            values = []
            for key in ("highest_accuracy", "accuracy", "baseline_accuracy"):
                value = data.get(key)
                if value is not None:
                    values.append(float(value))
            return max(values) if values else None
        except Exception:
            return None

    def get_incremental_training_context(
        self,
        game: str,
        *,
        requested_target: float | None = None,
    ) -> dict:
        """Summarize prior model state for incremental (build-on-previous) training."""
        game_key = str(game or "").strip().lower()
        model_path = os.path.join(self.models_dir, f"{game_key}_model.joblib")
        has_saved_model = os.path.exists(model_path)
        baseline = self._load_stored_baseline(game_key)
        requested = float(
            requested_target if requested_target is not None else self.target_accuracy
        )
        requested = min(0.99, max(0.5, requested))
        training_target = max(requested, baseline or 0.0)
        stored_meta: dict = {}
        experiments_dir = os.path.join(os.path.dirname(self.models_dir), "experiments")
        metadata_path = os.path.join(experiments_dir, f"{game_key}_model_metadata.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r") as handle:
                    loaded = json.load(handle)
                    if isinstance(loaded, dict):
                        stored_meta = loaded
            except Exception:
                stored_meta = {}

        return {
            "game": game_key,
            "has_saved_model": has_saved_model,
            "highest_accuracy": baseline,
            "baseline_accuracy": baseline,
            "requested_target_accuracy": requested,
            "training_target": training_target,
            "incremental_learning": bool(has_saved_model or baseline is not None),
            "blend_step": float(self.blend_step),
            "model_type": "RandomForestRegressor",
            "model_strategy": stored_meta.get("model_strategy"),
            "blend_weight": stored_meta.get("blend_weight"),
            "accuracy_history": stored_meta.get("accuracy_history") or [],
            "recent_runs": stored_meta.get("recent_runs") or [],
        }

    def _resolve_baseline_accuracy(
        self,
        game: str,
        model_baseline: float | None,
    ) -> float | None:
        """Return the highest known accuracy across model artifact and metadata."""
        values = []
        if model_baseline is not None:
            values.append(float(model_baseline))
        stored = self._load_stored_baseline(game)
        if stored is not None:
            values.append(float(stored))
        return max(values) if values else None

    def _load_previous_state(self, model_path: str, X_val, y_val, y_full):
        previous_artifact = None
        previous_model = None
        previous_accuracy = None
        previous_mae = None
        previous_predictions = None

        if not os.path.exists(model_path):
            return previous_artifact, previous_model, previous_accuracy, previous_mae, previous_predictions

        try:
            existing_artifact = joblib.load(model_path)
            if not isinstance(existing_artifact, dict):
                return previous_artifact, previous_model, previous_accuracy, previous_mae, previous_predictions

            previous_artifact = existing_artifact
            previous_model = existing_artifact.get("model")
            if previous_model is None:
                return previous_artifact, previous_model, previous_accuracy, previous_mae, previous_predictions

            previous_predictions = self._predict_with_artifact(existing_artifact, X_val)
            previous_mae, live_accuracy = self._score_predictions(y_val, previous_predictions, y_full)
            previous_accuracy = self._baseline_accuracy(existing_artifact, live_accuracy)
            if previous_accuracy is not None and previous_mae is not None:
                return previous_artifact, previous_model, previous_accuracy, previous_mae, previous_predictions
        except Exception:
            pass

        return None, None, None, None, None

    def _find_best_blend(self, candidate_predictions, previous_predictions, y_val, y_full):
        best = None
        step = self.blend_step if self.blend_step > 0 else 0.1
        weight = step
        while weight < 1.0:
            blend_pred = (weight * candidate_predictions) + ((1.0 - weight) * previous_predictions)
            mae, accuracy = self._score_predictions(y_val, blend_pred, y_full)
            if best is None or accuracy > best["accuracy"]:
                best = {
                    "weight": float(weight),
                    "mae": float(mae),
                    "accuracy": float(accuracy),
                }
            weight = round(weight + step, 10)
        return best

    def _train_recursive(
        self,
        X_train,
        y_train,
        X_val,
        y_val,
        y_full,
        attempt: int = 1,
        best_result: dict | None = None,
        floor_accuracy: float | None = None,
        training_target: float | None = None,
    ):
        model, mae, accuracy, predictions = self._fit_and_score_model(X_train, y_train, X_val, y_val, y_full, attempt)
        target = float(training_target if training_target is not None else self.target_accuracy)
        floor = float(floor_accuracy) if floor_accuracy is not None else None

        current = {
            "model": model,
            "mae": mae,
            "accuracy": accuracy,
            "attempt": attempt,
            "predictions": predictions,
        }

        if best_result is None or accuracy > best_result["accuracy"]:
            best_result = current

        beat_floor = floor is None or accuracy >= floor
        if beat_floor and accuracy >= target:
            return {
                **current,
                "reached_target": True,
                "attempts": attempt,
            }

        if attempt >= self.max_train_attempts:
            return {
                **best_result,
                "reached_target": bool(
                    best_result["accuracy"] >= target
                    and (floor is None or best_result["accuracy"] >= floor)
                ),
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
            floor_accuracy=floor_accuracy,
            training_target=training_target,
        )

    def train_model(self, game: str):
        from .chroma_client import chroma_client

        collection = chroma_client.client.get_collection(game)
        metadatas = self._load_all_metadatas(collection)
        if not metadatas:
            return {"status": "error", "message": "No data found to train on."}

        metadatas = self._sort_metadatas_chronologically(metadatas)
        window_size = max(1, int(self.window_size or 1))
        sequences = self._extract_winning_sequences(metadatas, game)
        X, y, feature_len, output_len = self._build_supervised_dataset(sequences, window_size)
        if X is None or len(X) < 10:
            return {"status": "error", "message": "Not enough parsed winning-number sequences to train."}

        model_path = os.path.join(self.models_dir, f"{game}_model.joblib")
        requested_target = float(self.target_accuracy)
        baseline_accuracy = self._resolve_baseline_accuracy(game, None)
        reported_previous_accuracy = float(baseline_accuracy) if baseline_accuracy is not None else None
        training_target = max(requested_target, baseline_accuracy or 0.0)

        best_run = None
        total_attempts = 0
        for train_size in self._train_size_candidates():
            train_size = min(max(float(train_size), 0.10), 0.50)
            val_size = 1.0 - train_size
            X_train, X_val, y_train, y_val = self._chronological_split(X, y, train_size)
            (
                previous_artifact,
                previous_model,
                previous_accuracy,
                previous_mae,
                previous_predictions,
            ) = self._load_previous_state(model_path, X_val, y_val, y)

            if baseline_accuracy is None and previous_accuracy is not None:
                baseline_accuracy = self._resolve_baseline_accuracy(game, previous_accuracy)
                reported_previous_accuracy = (
                    float(baseline_accuracy) if baseline_accuracy is not None else previous_accuracy
                )
                training_target = max(requested_target, baseline_accuracy or 0.0)

            candidates = self._train_iterative_collect(X_train, y_train, X_val, y_val, y)
            if previous_model is not None and previous_predictions is not None:
                try:
                    prev_mae, prev_acc = self._score_predictions(y_val, previous_predictions, y)
                    candidates.append(
                        {
                            "model": previous_model,
                            "mae": float(prev_mae),
                            "accuracy": float(prev_acc),
                            "attempt": 0,
                            "predictions": np.asarray(previous_predictions, dtype=float),
                        }
                    )
                except Exception:
                    pass

            if not candidates:
                continue

            total_attempts += len(candidates)
            selected_candidate = self._select_best_candidate(candidates, y_val, y)
            if selected_candidate is None:
                continue

            run_payload = {
                **selected_candidate,
                "train_size": train_size,
                "validation_size": val_size,
                "X_val": X_val,
                "y_val": y_val,
                "previous_artifact": previous_artifact,
                "previous_model": previous_model,
                "previous_accuracy": previous_accuracy,
                "previous_mae": previous_mae,
                "previous_predictions": previous_predictions,
                "attempts": len(candidates),
            }
            if best_run is None or float(run_payload["accuracy"]) > float(best_run["accuracy"]):
                best_run = run_payload

        if best_run is None:
            return {"status": "error", "message": "No successful training attempts were completed."}

        train_size = float(best_run["train_size"])
        val_size = float(best_run["validation_size"])
        X_val = best_run["X_val"]
        y_val = best_run["y_val"]
        previous_artifact = best_run["previous_artifact"]
        previous_model = best_run["previous_model"]
        previous_accuracy = best_run["previous_accuracy"]
        previous_mae = best_run["previous_mae"]
        previous_predictions = best_run["previous_predictions"]

        candidate_model = best_run["model"]
        candidate_predictions = np.asarray(best_run.get("predictions"), dtype=float)
        candidate_mae = float(best_run["mae"])
        candidate_accuracy = float(best_run["accuracy"])
        candidate_strategy = best_run["strategy"]
        candidate_top_models = best_run.get("top_models")
        candidate_ensemble_weights = best_run.get("ensemble_weights")
        candidate_top_k_accuracies = best_run.get("top_k_accuracies")

        train_result = {
            "model": candidate_model,
            "mae": candidate_mae,
            "accuracy": candidate_accuracy,
            "predictions": candidate_predictions,
            "attempts": total_attempts,
            "reached_target": bool(
                candidate_accuracy >= training_target
                and (baseline_accuracy is None or candidate_accuracy >= baseline_accuracy)
            ),
        }

        try:
            if candidate_strategy == "ensemble_top3" and candidate_top_models:
                full_dataset_predictions = self._ensemble_predictions(
                    candidate_top_models,
                    candidate_ensemble_weights or [],
                    X,
                )
            else:
                full_dataset_predictions = candidate_model.predict(X)
            full_dataset_mae, full_dataset_accuracy = self._score_predictions(
                y, full_dataset_predictions, y
            )
        except Exception:
            full_dataset_mae = None
            full_dataset_accuracy = None

        selected_strategy = candidate_strategy
        selected_model = candidate_model
        selected_secondary_model = None
        selected_blend_weight = None
        selected_top_models = candidate_top_models
        selected_ensemble_weights = candidate_ensemble_weights
        selected_top_k_accuracies = candidate_top_k_accuracies
        selected_accuracy = candidate_accuracy
        selected_mae = candidate_mae
        retained_previous_model = False
        used_previous_training = previous_predictions is not None
        floor_accuracy = float(baseline_accuracy) if baseline_accuracy is not None else None

        def _apply_previous_artifact():
            nonlocal selected_strategy, selected_model, selected_secondary_model
            nonlocal selected_blend_weight, selected_top_models, selected_ensemble_weights
            nonlocal selected_top_k_accuracies, selected_accuracy, selected_mae, retained_previous_model
            if previous_model is None:
                return
            selected_strategy = str((previous_artifact or {}).get("model_strategy", "single"))
            selected_model = (previous_artifact or {}).get("model")
            selected_secondary_model = (previous_artifact or {}).get("secondary_model")
            selected_blend_weight = (previous_artifact or {}).get("blend_weight")
            selected_top_models = (previous_artifact or {}).get("top_models")
            selected_ensemble_weights = (previous_artifact or {}).get("ensemble_weights")
            selected_top_k_accuracies = ((previous_artifact or {}).get("metrics") or {}).get(
                "top_k_accuracies"
            )
            selected_accuracy = float(
                baseline_accuracy if baseline_accuracy is not None else previous_accuracy
            )
            selected_mae = float(previous_mae) if previous_mae is not None else selected_mae
            retained_previous_model = True

        if floor_accuracy is not None and selected_accuracy < floor_accuracy:
            _apply_previous_artifact()
        elif previous_accuracy is not None and previous_accuracy > selected_accuracy:
            _apply_previous_artifact()

        blend_candidate = None
        if (
            candidate_strategy != "ensemble_top3"
            and previous_predictions is not None
            and previous_model is not None
        ):
            blend_candidate = self._find_best_blend(candidate_predictions, previous_predictions, y_val, y)

        blend_accuracy = float(blend_candidate["accuracy"]) if blend_candidate else None
        blend_beats_floor = floor_accuracy is None or (
            blend_accuracy is not None and blend_accuracy >= floor_accuracy
        )
        if (
            blend_candidate is not None
            and previous_model is not None
            and blend_accuracy is not None
            and blend_beats_floor
            and blend_accuracy > selected_accuracy
        ):
            selected_strategy = "ensemble"
            selected_model = candidate_model
            selected_secondary_model = previous_model
            selected_blend_weight = float(blend_candidate["weight"])
            selected_top_models = None
            selected_ensemble_weights = None
            selected_top_k_accuracies = None
            selected_accuracy = blend_accuracy
            selected_mae = float(blend_candidate["mae"])
            retained_previous_model = False

        if floor_accuracy is not None and selected_accuracy < floor_accuracy:
            _apply_previous_artifact()

        artifact = {
            "model": selected_model,
            "secondary_model": selected_secondary_model,
            "blend_weight": selected_blend_weight,
            "model_strategy": selected_strategy,
            "top_models": selected_top_models,
            "ensemble_weights": selected_ensemble_weights,
            "feature_len": feature_len,
            "output_len": output_len,
            "game": game,
            "rules": self._get_rules(game),
            "version": 4,
            "window_size": int(window_size),
            "metrics": {
                "accuracy": selected_accuracy,
                "mae": selected_mae,
                "attempts": int(train_result.get("attempts", 1)),
                "reached_target": bool(train_result.get("reached_target", False)),
                "target_accuracy": requested_target,
                "training_target": training_target,
                "baseline_accuracy": baseline_accuracy,
                "train_size": train_size,
                "validation_size": val_size,
                "n_estimators": int(self.n_estimators),
                "max_depth": int(self.max_depth),
                "random_state": int(self.random_state),
                "records_loaded": len(metadatas),
                "window_size": int(window_size),
                "auto_tune": bool(self.auto_tune),
                "split_strategy": "chronological",
                "candidate_accuracy": candidate_accuracy,
                "candidate_mae": candidate_mae,
                "previous_accuracy": reported_previous_accuracy,
                "previous_mae": previous_mae,
                "used_previous_training": used_previous_training,
                "model_strategy": selected_strategy,
                "blend_weight": selected_blend_weight,
                "top_k_accuracies": selected_top_k_accuracies,
                "full_dataset_accuracy": full_dataset_accuracy,
                "full_dataset_mae": full_dataset_mae,
            },
        }

        highest_accuracy = float(selected_accuracy) if selected_accuracy is not None else None
        experiments_dir = os.path.join(os.path.dirname(self.models_dir), "experiments")
        os.makedirs(experiments_dir, exist_ok=True)
        metadata_path = os.path.join(experiments_dir, f"{game}_model_metadata.json")
        existing_meta: dict = {}
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r") as handle:
                    loaded = json.load(handle)
                    if isinstance(loaded, dict):
                        existing_meta = loaded
            except Exception:
                existing_meta = {}

        from experiments.store import update_accuracy_history

        accuracy_history = update_accuracy_history(
            existing_meta.get("accuracy_history"),
            highest_accuracy,
        )
        recent_runs = list(existing_meta.get("recent_runs") or [])
        recent_runs.insert(
            0,
            {
                "timestamp": time.time(),
                "accuracy": highest_accuracy,
                "retained_previous_model": bool(retained_previous_model),
            },
        )
        recent_runs = recent_runs[:3]

        metadata_to_save = {
            "game": game,
            "model_type": "RandomForestRegressor",
            "accuracy": highest_accuracy,
            "highest_accuracy": highest_accuracy,
            "mae": float(selected_mae) if selected_mae is not None else None,
            "feature_len": int(feature_len),
            "output_len": int(output_len),
            "samples": int(len(X)),
            "target_accuracy": float(requested_target),
            "training_target": float(training_target),
            "baseline_accuracy": float(baseline_accuracy) if baseline_accuracy is not None else None,
            "attempts": int(train_result.get("attempts", 1)),
            "reached_target": bool(train_result.get("reached_target", False)) or bool(
                highest_accuracy is not None and highest_accuracy >= training_target
            ),
            "retained_previous_model": bool(retained_previous_model),
            "used_previous_training": bool(used_previous_training),
            "model_strategy": str(selected_strategy),
            "blend_weight": float(selected_blend_weight) if selected_blend_weight is not None else None,
            "candidate_accuracy": float(candidate_accuracy) if candidate_accuracy is not None else None,
            "previous_accuracy": float(reported_previous_accuracy)
            if reported_previous_accuracy is not None
            else None,
            "train_size": float(train_size),
            "validation_size": float(val_size),
            "last_trained_at": time.time(),
            "accuracy_history": accuracy_history,
            "recent_runs": recent_runs,
        }
        try:
            with open(metadata_path, "w") as f:
                json.dump(metadata_to_save, f, indent=2)
        except Exception as exc:
            print(f"WARNING: Failed to save model metadata JSON for {game}: {exc}")

        if retained_previous_model:
            return {
                "status": "success",
                "message": (
                    f"Training completed for {game}. Using highest current accuracy "
                    f"({reported_previous_accuracy:.4f}) — new candidate ({candidate_accuracy:.4f}) did not improve."
                ),
                "accuracy": reported_previous_accuracy,
                "highest_accuracy": highest_accuracy,
                "previous_accuracy": reported_previous_accuracy,
                "candidate_accuracy": candidate_accuracy,
                "new_accuracy": candidate_accuracy,
                "mae": selected_mae,
                "model_path": model_path,
                "feature_len": feature_len,
                "output_len": output_len,
                "samples": int(len(X)),
                "target_accuracy": requested_target,
                "training_target": training_target,
                "baseline_accuracy": baseline_accuracy,
                "attempts": int(train_result.get("attempts", 1)),
                "reached_target": bool(
                    highest_accuracy is not None and highest_accuracy >= training_target
                ),
                "retained_previous_model": True,
                "used_previous_training": used_previous_training,
                "model_strategy": selected_strategy,
                "blend_weight": selected_blend_weight,
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
            "message": (
                f"Trained {game} model with highest current accuracy "
                f"({selected_accuracy:.4f})."
            ),
            "accuracy": selected_accuracy,
            "highest_accuracy": highest_accuracy,
            "mae": selected_mae,
            "model_path": model_path,
            "feature_len": feature_len,
            "output_len": output_len,
            "samples": int(len(X)),
            "target_accuracy": requested_target,
            "training_target": training_target,
            "baseline_accuracy": baseline_accuracy,
            "attempts": int(train_result.get("attempts", 1)),
            "reached_target": bool(
                train_result.get("reached_target", False)
                or (selected_accuracy is not None and selected_accuracy >= training_target)
            ),
            "retained_previous_model": False,
            "used_previous_training": used_previous_training,
            "model_strategy": selected_strategy,
            "blend_weight": selected_blend_weight,
            "candidate_accuracy": candidate_accuracy,
            "previous_accuracy": reported_previous_accuracy,
            "train_size": train_size,
            "validation_size": val_size,
        }

    def train(
        self,
        game: str,
        target_accuracy: float = None,
        max_iterations: int = None,
        train_size: float = None,
        n_estimators: int = None,
        max_depth: int = None,
        random_state: int = None,
        blend_step: float = None,
        data_limit: int = None,
        window_size: int = None,
        auto_tune: bool = None,
    ):
        """Backward-compatible alias used by API routes and tooling."""
        self.configure_training(
            target_accuracy=target_accuracy,
            max_iterations=max_iterations,
            train_size=train_size,
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            blend_step=blend_step,
            data_limit=data_limit,
            window_size=window_size,
            auto_tune=auto_tune,
        )
        return self.train_model(game)

    def train_all_games(self, games: list[str] | None = None):
        from config import GAME_CONFIGS

        targets = games or list(GAME_CONFIGS.keys())
        results = []
        for game in targets:
            try:
                results.append({"game": game, **self.train_model(game)})
            except Exception as exc:
                results.append({"game": game, "status": "error", "message": str(exc)})
        return results


trainer_service = TrainerService()
