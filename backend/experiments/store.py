import json
import os
from typing import List, Dict, Any

class ExperimentStore:
    def __init__(self, store_path: str):
        self.store_path = store_path
        self._ensure_store_exists()

    def _ensure_store_exists(self):
        if not os.path.exists(self.store_path):
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            with open(self.store_path, "w") as f:
                json.dump([], f)

    def list_experiments(self) -> List[Dict[str, Any]]:
        with open(self.store_path, "r") as f:
            return json.load(f)

    def save_experiment(self, experiment_data: Dict[str, Any]):
        experiments = self.list_experiments()
        experiments.append(experiment_data)
        with open(self.store_path, "w") as f:
            json.dump(experiments, f, indent=2)
