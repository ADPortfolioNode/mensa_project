import React, { useState } from 'react';
import axios from 'axios';
import PredictionDisplay from './PredictionDisplay';
import './PredictionDisplay.css';

// Normalize API base: trim, strip trailing slashes, and ensure scheme when provided
function normalizeApiBase(raw) {
  const v = (raw || '').toString().trim().replace(/\/+$/, '');
  if (!v) return '';
  // If missing http/https scheme, assume http:// for convenience
  if (!/^https?:\/\//i.test(v)) {
    return `http://${v}`;
  }
  return v;
}

const API_BASE = normalizeApiBase(process.env.REACT_APP_API_BASE);

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
      const r = await axios.post(`${API_BASE}/api/predict`, {
        game: game,
        recent_k: parseInt(recentK, 10)
      });
      setPrediction(r.data.prediction);
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
          <div className="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style={{ width: '100%' }}></div>
        </div>
      )}
      {error && !loading && (
        <div className="alert alert-danger">
          <strong>Error:</strong> {error}
        </div>
      )}
      {prediction && !loading && !error && (
        prediction[game] && prediction[game].error ? (
          <div className="alert alert-danger">
            <strong>Error:</strong> {prediction[game].error}
          </div>
        ) : (
          <PredictionDisplay prediction={prediction[game]} />
        )
      )}
    </div>
  );
}
