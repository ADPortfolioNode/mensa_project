import React from 'react';
import PredictionDisplay from './PredictionDisplay';
import { formatNextGameDateLabel } from '../utils/suggestionUtils';

export default function AllPredictionsPanel({ predictions }) {
  if (!predictions || predictions.length === 0) {
    return null;
  }

  return (
    <div className="card p-3 mb-3">
      <h5>All Suggestions</h5>
      {predictions.map((item) => {
        const prediction = item.prediction
          ? { ...item.prediction, game: item.prediction.game || item.game }
          : null;
        const scheduleLabel = prediction ? formatNextGameDateLabel(prediction) : '';

        return (
          <div key={item.game} className="mb-3">
            <h6 className="mb-1">{item.game.toUpperCase()}</h6>
            {scheduleLabel && (
              <div className="small text-muted mb-2">{scheduleLabel}</div>
            )}
            {item.status === 'error' ? (
              <div className="alert alert-danger mb-0">
                <strong>Error:</strong> {item.message || 'Suggestion failed.'}
              </div>
            ) : (
              <PredictionDisplay prediction={prediction} />
            )}
          </div>
        );
      })}
    </div>
  );
}
