import os
import numpy as np
from tensorflow import keras

class PredictorService:
    def __init__(self):
        self.models_dir = "/data/models"

    def predict_next_draw(self, game: str, recent_k: int = 10):
        # Lazy import to avoid ChromaDB connection during module import
        from .chroma_client import chroma_client
        
        model_path = os.path.join(self.models_dir, f"{game}_model.h5")
        if not os.path.exists(model_path):
            return {"status": "error", "message": f"Model for game '{game}' not found."}

        model = keras.models.load_model(model_path)

        # Fetch recent draws from ChromaDB for prediction input
        collection = chroma_client.client.get_collection(game)
        data = collection.get(limit=recent_k)  # Get recent entries
        
        if not data or not data['metadatas']:
             return {"status": "error", "message": "Not enough data to make a prediction."}
        
        # Process the recent draws to create a sequence
        sequences = []
        for meta in data['metadatas']:
            winning_str = meta.get('winning_numbers', '')
            if winning_str:
                try:
                    nums = [int(n) for n in winning_str.split() if n.isdigit()]
                    sequences.append(nums[:10])  # Take first 10 numbers
                except:
                    continue
        
        if not sequences:
            return {"status": "error", "message": "No valid sequences found."}
        
        # Use the most recent sequence
        seq = sequences[0]
        max_len = model.input_shape[1]  # Get max_len from model
        seq = seq + [0] * (max_len - len(seq)) if len(seq) < max_len else seq[:max_len]
        
        X = np.array([seq]).reshape((1, max_len, 1))
        
        prediction = model.predict(X)
        
        # Round to nearest integers
        predicted_numbers = [int(np.round(p)) for p in prediction[0]]
        
        return {"prediction": predicted_numbers}

# Export a module-level instance expected by main_rag and other modules
predictor_service = PredictorService()
