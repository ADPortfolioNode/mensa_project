import os
import numpy as np
import pandas as pd
from typing import Tuple

from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split


class Agent:
    """Lightweight abstraction representing an 'agent' layer group.

    This is primarily a code-organization aid to match the "agentic" design
    described in the task: an input-agent, several mid-layer agents, and
    an output-agent. Internally these return Keras layers.
    """
    def __init__(self, name: str):
        self.name = name

    def input_agent(self, input_shape: Tuple[int, int]):
        # Encode features from game history
        return [layers.Input(shape=input_shape)]

    def mid_agents(self):
        # Perform data tracing across nodes (conv blocks)
        return [
            layers.Conv1D(32, 3, activation="relu", padding="same"),
            layers.MaxPooling1D(2),
            layers.Conv1D(64, 3, activation="relu", padding="same"),
            layers.Conv1D(128, 3, activation="relu", padding="same"),
            layers.GlobalMaxPooling1D(),
            layers.Dense(128, activation="relu"),
        ]

    def output_agent(self, output_size: int):
        # Produce numeric outputs for predicted draw (linear for regression)
        return layers.Dense(output_size, activation="linear")


class TrainerService:
    def __init__(self):
        self.models_dir = "/data/models"
        os.makedirs(self.models_dir, exist_ok=True)

    def _parse_metadatas(self, data) -> pd.DataFrame:
        df = pd.DataFrame(data.get("metadatas", []))
        # Attempt to find a column that contains the winning numbers
        winning_col = None
        for col in df.columns:
            if "winning" in col.lower() or "numbers" in col.lower():
                winning_col = col
                break
        if winning_col:
            df["winning_numbers"] = df[winning_col]
        return df

    def _make_sequences(self, df: pd.DataFrame, input_len: int = 10, output_len: int = 6):
        # Parse winning numbers to lists of ints
        df = df.copy()
        df["parsed_numbers"] = df["winning_numbers"].apply(
            lambda x: [int(n) for n in str(x).split() if n.isdigit()]
        )
        df = df[df["parsed_numbers"].apply(len) > 0]

        sequences, labels = [], []
        for i in range(1, len(df)):
            seq = df.iloc[i - 1]["parsed_numbers"][:input_len]
            label = df.iloc[i]["parsed_numbers"][:output_len]
            if len(label) < output_len:
                label = label + [0] * (output_len - len(label))
            sequences.append(seq)
            labels.append(label)

        if not sequences:
            return None, None, 0

        max_len = max(len(s) for s in sequences)
        sequences = [s + [0] * (max_len - len(s)) for s in sequences]
        X = np.array(sequences)
        y = np.array(labels)
        return X, y, max_len

    def train_model(self, game: str, target_accuracy: float = 0.98, max_iterations: int = 10):
        """Train an agentic CNN model for `game`.

        Design notes (implements user's spec):
        - Input-agent encodes historical features.
        - Several mid-layer agents perform data tracing (Conv1D blocks).
        - Output-agent produces predicted draw numbers (linear regression output).
        - Data split: 1/3 training, 2/3 validation (as requested).
        - Iterative training loop continues until `target_accuracy` or `max_iterations`.
        """
        # Lazy import to avoid chroma at import time
        from .chroma_client import chroma_client

        collection = chroma_client.client.get_collection(game)
        data = collection.get()
        if not data or not data.get("metadatas"):
            return {"status": "error", "message": "No data found to train on."}

        df = self._parse_metadatas(data)
        if "winning_numbers" not in df.columns:
            return {"status": "error", "message": "No winning numbers column found in data."}

        X, y, seq_len = self._make_sequences(df)
        if X is None:
            return {"status": "error", "message": "No sequences generated from data."}

        # Split: 1/3 train, 2/3 validation
        test_size = 2 / 3
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=test_size, random_state=42)

        # reshape for Conv1D
        X_train = X_train.reshape((X_train.shape[0], X_train.shape[1], 1))
        X_val = X_val.reshape((X_val.shape[0], X_val.shape[1], 1))

        # Build agentic model
        input_agent = Agent("input")
        mid_agent = Agent("mid")
        output_agent = Agent("output")

        model_layers = []
        model_layers += input_agent.input_agent((seq_len, 1))
        model_layers += mid_agent.mid_agents()
        model_layers.append(output_agent.output_agent(y.shape[1]))

        model = keras.Sequential(model_layers)
        model.compile(optimizer="adam", loss="mse", metrics=["mae"]) 

        # Iterative training loop
        accuracy = 0.0
        iterations = 0
        while accuracy < target_accuracy and iterations < max_iterations:
            model.fit(X_train, y_train, epochs=5, verbose=1)
            preds = model.predict(X_val)
            mae = np.mean(np.abs(preds - y_val))
            max_val = np.max(y) if np.max(y) > 0 else 1
            accuracy = max(0.0, 1.0 - mae / max_val)
            iterations += 1
            print(f"Iteration {iterations}: MAE={mae:.4f}, Accuracy={accuracy:.4f}")

        model_path = os.path.join(self.models_dir, f"{game}_model.h5")
        model.save(model_path)

        return {
            "status": "success",
            "message": f"Trained {game} model",
            "iterations": iterations,
            "accuracy": float(accuracy),
            "model_path": model_path,
        }


trainer_service = TrainerService()
