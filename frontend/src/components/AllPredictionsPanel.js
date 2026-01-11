import React from 'react';

export default function AllPredictionsPanel({ predictions }) {
  if (!predictions || predictions.length === 0) {
    return null;
  }

  // Group predictions by game for better display
  const grouped = predictions.reduce((acc, pred) => {
    if (!acc[pred.game]) acc[pred.game] = [];
    acc[pred.game].push(pred);
    return acc;
  }, {});

  return (
    <div className="card p-3 mb-3">
      <h5>All Predictions</h5>
      {Object.entries(grouped).map(([game, preds]) => (
        <div key={game} className="mb-3">
          <h6>{game.charAt(0).toUpperCase() + game.slice(1)}</h6>
          <ul className="list-group">
            {preds.map((pred, index) => (
              <li key={index} className="list-group-item">
                <strong>Prediction {index + 1}:</strong> {JSON.stringify(pred.prediction)}
                <br /><small className="text-muted">Timestamp: {pred.timestamp}</small>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
