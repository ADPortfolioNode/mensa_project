import os
import joblib
from sklearn.ensemble import RandomForestClassifier
import pandas as pd

class TrainerService:
    def __init__(self):
        self.models_dir = "/data/models"
        os.makedirs(self.models_dir, exist_ok=True)

    def train_model(self, game: str):
        # Lazy import to avoid ChromaDB connection during module import
        from .chroma_client import chroma_client
        
        collection_name = game
        collection = chroma_client.client.get_collection(collection_name)
        data = collection.get()

        if not data or not data['metadatas']:
            return {"status": "error", "message": "No data found to train on."}

        # This is a placeholder for feature engineering.
        # You would need to convert the lottery data into features (X) and labels (y).
        # For this example, we'll create some dummy data.
        df = pd.DataFrame(data['metadatas'])
        
        # A real implementation would require parsing the 'winning_numbers' field.
        # This is a simplified example.
        if 'winning_numbers' not in df.columns:
            return {"status": "error", "message": "'winning_numbers' column not found in data."}
            
        # Example feature engineering: use the numbers themselves as features
        # This is not a good way to model lottery data, but it's an example.
        try:
            X = df['winning_numbers'].apply(lambda x: [int(n) for n in x.split()]).tolist()
            # Create dummy labels (e.g., predict the first number of the next draw)
            y = [x[0] for x in X[1:]]
            X = X[:-1]
        except Exception as e:
            return {"status": "error", "message": f"Error during feature engineering: {e}"}


        if not X or not y:
            return {"status": "error", "message": "Not enough data to train the model."}

        model = RandomForestClassifier(n_estimators=100)
        model.fit(X, y)

        model_path = os.path.join(self.models_dir, f"{game}_model.joblib")
        joblib.dump(model, model_path)

        return {"status": "success", "message": f"Model for {game} trained and saved to {model_path}."}

trainer_service = TrainerService()
