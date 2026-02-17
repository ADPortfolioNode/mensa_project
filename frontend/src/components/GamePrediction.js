import React, { useState } from 'react';
import axios from 'axios';
import getApiBase from '../utils/apiBase';
import PredictionDisplay from './PredictionDisplay';
import './PredictionDisplay.css';

export default function GamePrediction({ game }) {
  const [recentK, setRecentK] = useState(10);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const submit = async () => {
    setLoading(true);
    setError(null);
    setPrediction(null);
    try {
      const apiBase = getApiBase();
      const r = await axios.post(`${apiBase}/api/predict`, {
        game: game,
        recent_k: parseInt(recentK, 10)
      });
      const payload = r.data || {};
      if (payload.status === 'error') {
        setError(payload.message || 'Prediction failed');
        return;
      }
      if (!payload.predicted_numbers) {
        setError('Prediction response did not include predicted numbers.');
        return;
      }
      setPrediction(payload);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Prediction failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card p-3 mb-3">
      <h5>Prediction for {game}</h5>
      <p>Enter the number of recent draws to consider for prediction (e.g., 10)</p>
      <div className="input-group mb-2">
        <input type="number" className="form-control" value={recentK} onChange={e => setRecentK(e.target.value)} disabled={loading} min="1" />
        <button className="btn btn-success" onClick={submit} disabled={loading}>
          {loading ? 'Loading...' : 'Predict'}
        </button>
      </div>
      {loading && (
        <div className="progress">
          <div className="progress-bar progress-bar-striped progress-bar-animated w-100" role="progressbar"></div>
        </div>
      )}
      {error && !loading && (
        <div className="alert alert-danger">
          <strong>Error:</strong> {error}
        </div>
      )}
      {prediction && !loading && !error && (
        prediction.error ? (
          <div className="alert alert-danger">
            <strong>Error:</strong> {prediction.error}
          </div>
        ) : (
          <PredictionDisplay prediction={prediction} />
        )
      )}
    </div>
  );
}
