import os
import joblib
import numpy as np

class PredictorService:
    def __init__(self):
        self.models_dir = "/data/models"

    def predict_next_draw(self, game: str, recent_k: int = 10):
        # Lazy import to avoid ChromaDB connection during module import
        from .chroma_client import chroma_client
        
        model_path = os.path.join(self.models_dir, f"{game}_model.joblib")
        if not os.path.exists(model_path):
            return {"status": "error", "message": f"Model for game '{game}' not found."}

        model = joblib.load(model_path)

        # In a real application, you would fetch the 'recent_k' draws from ChromaDB
        # and use them as input for the prediction.
        # This is a placeholder for that logic.
        collection = chroma_client.client.get_collection(game)
        data = collection.get(limit=recent_k, sort="desc") # Assuming ChromaDB has a sort feature
        
        if not data or not data['metadatas']:
             return {"status": "error", "message": "Not enough data to make a prediction."}
        
        # This assumes the same feature engineering as in the trainer
        try:
            X = [int(n) for n in data['metadatas'][0]['winning_numbers'].split()]
            # The model expects a list of lists
            X = [X]
        except Exception as e:
            return {"status": "error", "message": f"Error processing data for prediction: {e}"}

        prediction = model.predict(X)
        
        # The output of the model is a numpy array
        # We need to convert it to a list of integers
        return {"prediction": prediction.tolist()}

predictor_service = PredictorService()
