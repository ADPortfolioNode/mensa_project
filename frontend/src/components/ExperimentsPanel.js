import React from 'react';
import { formatExperimentTimestamp } from '../utils/timestampUtils';

export default function ExperimentsPanel({ experiments }) {
  return (
    <div className="card p-3">
      <h5>Experiments</h5>
      {experiments.length === 0 ? (
        <p>No experiments found.</p>
      ) : (
        <div className="table-responsive">
          <table className="table table-sm">
            <thead>
              <tr>
                <th>ID</th>
                <th>Game</th>
                <th>Status</th>
                <th>Accuracy</th>
                <th>Description</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {experiments.map(exp => (
                <tr key={exp.experiment_id}>
                  <td title={exp.experiment_id}>{exp.experiment_id.slice(0, 8)}...</td>
                  <td>{exp.game}</td>
                  <td>{exp.status || 'N/A'}</td>
                  <td>{((exp.score ?? exp.final_accuracy ?? exp.accuracy) != null ? `${(Number(exp.score ?? exp.final_accuracy ?? exp.accuracy) * 100).toFixed(2)}%` : 'N/A')}</td>
                  <td>{exp.description || exp.message || exp.error || 'N/A'}</td>
                  <td>{formatExperimentTimestamp(exp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
