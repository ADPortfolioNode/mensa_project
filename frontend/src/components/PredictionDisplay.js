import React from 'react';
import './PredictionDisplay.css';

const PredictionDisplay = ({ prediction }) => {
  if (!prediction || !prediction.predicted_numbers) {
    return null;
  }

  const formatted = prediction.formatted_prediction || null;
  const mainNumbers = formatted?.main_numbers || prediction.predicted_numbers;
  const bonusNumbers = formatted?.bonus_numbers || [];
  const mainLabel = formatted?.main_label || 'Numbers';
  const bonusLabel = formatted?.bonus_label || 'Bonus';
  const explicitBonusLabel = bonusNumbers.length > 1
    ? `Bonus Numbers (${bonusLabel})`
    : `Bonus Number (${bonusLabel})`;

  return (
    <div className="prediction-display">
      <h6 className="prediction-header">Predicted Numbers</h6>
      <div className="prediction-group">
        <div className="prediction-label">{mainLabel}</div>
        <div className="prediction-numbers">
          {mainNumbers.map((number, index) => (
            <div key={`main-${index}`} className="prediction-number">
              {number}
            </div>
          ))}
        </div>
      </div>

      {bonusNumbers.length > 0 && (
        <div className="prediction-group bonus-group">
          <div className="prediction-label">{explicitBonusLabel}</div>
          <div className="prediction-numbers">
            {bonusNumbers.map((number, index) => (
              <div key={`bonus-${index}`} className="prediction-number prediction-number-bonus">
                {number}
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};

export default PredictionDisplay;
