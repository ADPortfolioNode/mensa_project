import React from 'react';
import './PredictionDisplay.css';

const PredictionDisplay = ({ prediction }) => {
  if (!prediction || !prediction.predicted_numbers) {
    return null;
  }

  return (
    <div className="prediction-display">
      <h6 className="prediction-header">Predicted Numbers</h6>
      <div className="prediction-numbers">
        {prediction.predicted_numbers.map((number, index) => (
          <div key={index} className="prediction-number">
            {number}
          </div>
        ))}
      </div>
    </div>
  );
};

export default PredictionDisplay;
