import React from 'react';
import './PredictionDisplay.css';

const PredictionDisplay = ({ prediction }) => {
  if (!prediction) {
    return null;
  }

  const session = Array.isArray(prediction.prediction_session)
    ? prediction.prediction_session
    : [];
  const hasSession = session.length > 0;

  const renderPredictionBlock = (predictionItem, keyPrefix) => {
    const formatted = predictionItem?.formatted_prediction || null;
    const mainNumbers = formatted?.main_numbers || predictionItem?.predicted_numbers || [];
    const bonusNumbers = formatted?.bonus_numbers || [];
    const mainLabel = formatted?.main_label || 'Numbers';
    const bonusLabel = formatted?.bonus_label || 'Bonus';
    const explicitBonusLabel = bonusNumbers.length > 1
      ? `Bonus Numbers (${bonusLabel})`
      : `Bonus Number (${bonusLabel})`;

    return (
      <>
        <div className="prediction-group">
          <div className="prediction-label">{mainLabel}</div>
          <div className="prediction-numbers">
            {mainNumbers.map((number, index) => (
              <div key={`${keyPrefix}-main-${index}`} className="prediction-number">
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
                <div key={`${keyPrefix}-bonus-${index}`} className="prediction-number prediction-number-bonus">
                  {number}
                </div>
              ))}
            </div>
          </div>
        )}
      </>
    );
  };

  if (hasSession && session.length > 1) {
    // Show model metadata at the top if available
    const meta = prediction.model_metadata || {};
    return (
      <div className="prediction-display">
        <h6 className="prediction-header">Predicted Numbers ({session.length} Draws)</h6>
        <div className="text-muted mb-2">
          {prediction.predicted_for_date && (
            <span>Session Date: {prediction.predicted_for_date}</span>
          )}
          {meta.model_strategy && (
            <span style={{ marginLeft: 12 }}>Strategy: {meta.model_strategy}</span>
          )}
          {meta.blend_weight !== undefined && (
            <span style={{ marginLeft: 12 }}>Blend: {meta.blend_weight}</span>
          )}
          {meta.used_previous_training !== undefined && (
            <span style={{ marginLeft: 12 }}>PrevTrain: {meta.used_previous_training ? 'Yes' : 'No'}</span>
          )}
        </div>
        {session.map((draw) => (
          <div key={`draw-${draw.draw_index}`} className="mb-3">
            <div className="prediction-label mb-1">
              Draw {draw.draw_index}
              {draw.prediction_date && (
                <span className="text-muted" style={{ marginLeft: 8, fontSize: '0.95em' }}>
                  {draw.prediction_date}
                  {draw.prediction_weekday ? ` (${draw.prediction_weekday})` : ''}
                  {draw.prediction_timezone ? ` [${draw.prediction_timezone}]` : ''}
                </span>
              )}
            </div>
            {renderPredictionBlock(draw, `draw-${draw.draw_index}`)}
          </div>
        ))}
      </div>
    );
  }

  const singlePrediction = hasSession ? session[0] : prediction;
  const singleNumbers = Array.isArray(singlePrediction?.predicted_numbers)
    ? singlePrediction.predicted_numbers
    : [];
  if (singleNumbers.length === 0) {
    if (prediction.message) {
      return <div className="text-muted">{prediction.message}</div>;
    }
    return null;
  }

  // Show model metadata for single prediction as well
  const meta = prediction.model_metadata || {};
  return (
    <div className="prediction-display">
      <h6 className="prediction-header">Predicted Numbers</h6>
      <div className="text-muted mb-2">
        {prediction.predicted_for_date && (
          <span>Date: {prediction.predicted_for_date}</span>
        )}
        {singlePrediction.prediction_date && (
          <span style={{ marginLeft: 12 }}>Draw: {singlePrediction.prediction_date}</span>
        )}
        {singlePrediction.prediction_weekday && (
          <span style={{ marginLeft: 8 }}>({singlePrediction.prediction_weekday})</span>
        )}
        {singlePrediction.prediction_timezone && (
          <span style={{ marginLeft: 8 }}>[{singlePrediction.prediction_timezone}]</span>
        )}
        {meta.model_strategy && (
          <span style={{ marginLeft: 12 }}>Strategy: {meta.model_strategy}</span>
        )}
        {meta.blend_weight !== undefined && (
          <span style={{ marginLeft: 12 }}>Blend: {meta.blend_weight}</span>
        )}
        {meta.used_previous_training !== undefined && (
          <span style={{ marginLeft: 12 }}>PrevTrain: {meta.used_previous_training ? 'Yes' : 'No'}</span>
        )}
      </div>
      {renderPredictionBlock(singlePrediction, 'single')}
    </div>
  );
};

export default PredictionDisplay;
