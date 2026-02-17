import React, { useState } from 'react';
import './TrainingCard.css';
import ProgressiveProgressBar from './ProgressiveProgressBar';

export default function TrainingCard({ trainStatus, trainProgress, iterations, accuracy, onTrain, selectedGame, disabled }) {
  const [expanded, setExpanded] = useState(false);

  const toggleExpanded = () => {
    setExpanded(!expanded);
  };

  return (
    <div className={`training-card ${expanded ? 'expanded' : ''}`}>
      <div className="training-card-header" onClick={toggleExpanded}>
        <h3>Model Training</h3>
        <div className="training-status">
          <span className={`status-badge ${trainStatus}`}>{trainStatus}</span>
<<<<<<< HEAD
          {trainStatus === 'in progress' && (
            <div className="training-progress-wrap">
              <progress className="training-progress" value={trainProgress} max="100" />
            </div>
          )}
=======
>>>>>>> 165dff8cc451c862093412a10d4f2db017f0a8f6
        </div>
        <button className="expand-btn">{expanded ? '−' : '+'}</button>
      </div>

      <div className="training-card-body">
        {trainStatus === 'in progress' && (
          <ProgressiveProgressBar
            current={trainProgress}
            total={100}
            status="active"
            label="Training Progress"
            showMetadata={false}
            colorScheme="success"
          />
        )}
        <button
          onClick={onTrain}
          disabled={disabled || !selectedGame}
          className="train-btn"
        >
          {trainStatus === 'in progress' ? 'Training...' : 'Start Training'}
        </button>

        {expanded && (
          <div className="training-details">
            <div className="detail-item">
              <label>Game:</label>
              <span>{selectedGame || 'None selected'}</span>
            </div>
            {iterations !== undefined && (
              <div className="detail-item">
                <label>Iterations:</label>
                <span>{iterations}</span>
              </div>
            )}
            {accuracy !== undefined && (
              <div className="detail-item">
                <label>Accuracy:</label>
                <span>{(accuracy * 100).toFixed(2)}%</span>
              </div>
            )}
            <div className="detail-item">
              <label>Progress:</label>
              <span>{trainProgress}%</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}