"""
Model utilities for loading and managing ML models.
"""
import joblib
from pathlib import Path
import os
from typing import Dict, Any


def _load_model_metadata(game_key: str) -> dict:
    """
    Load persisted model artifact metadata for a specific game.
    Returns empty dict if metadata file doesn't exist.
    """
    data_dir = os.environ.get('DATA_DIR', '/data')
    metadata_path = Path(data_dir) / 'experiments' / f'{game_key}_model_metadata.json'
    
    if not metadata_path.exists():
        return {}
    
    try:
        with open(metadata_path, 'r') as f:
            return joblib.load(f)
    except Exception as e:
        print(f"Failed to load model metadata for {game_key}: {e}")
        return {}