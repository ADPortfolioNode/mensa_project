import React, { useState, useEffect } from 'react';
import axios from 'axios';

function normalizeApiBase(raw) {
  const v = (raw || '').toString().trim().replace(/\/+$/, '');
  if (!v) return '';
  if (!/^https?:\/\//i.test(v)) {
    return `http://${v}`;
  }
  return v;
}

const API_BASE = normalizeApiBase(process.env.REACT_APP_API_BASE);

export default function GameSummaryPanel({ games }) {
  const [summaries, setSummaries] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (games && games.length > 0) {
      fetchSummaries();
    }
  }, [games]);

  const fetchSummaries = async () => {
    setLoading(true);
    setError(null);
    const newSummaries = {};
    for (const game of games) {
      try {
        const r = await axios.get(`${API_BASE}/api/games/${game}/summary`);
        newSummaries[game] = r.data.draw_count;
      } catch (e) {
        console.error(`Failed to fetch summary for ${game}:`, e);
        newSummaries[game] = 'Error';
        setError('Failed to fetch some game summaries.');
      }
    }
    setSummaries(newSummaries);
    setLoading(false);
  };

  return (
    <div className="card p-3 mb-3">
      <h5>Game Contents</h5>
      {loading && (
        <div className="progress mb-2">
          <div className="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style={{ width: '100%' }}></div>
        </div>
      )}
      {error && !loading && (
        <div className="alert alert-danger">
          <strong>Error:</strong> {error}
        </div>
      )}
      {games.length === 0 && !loading && <p>No games available.</p>}
      {!loading && games.length > 0 && (
        <ul className="list-group list-group-flush">
          {games.map(game => (
            <li key={game} className="list-group-item d-flex justify-content-between align-items-center">
              {game}
              <span className="badge bg-primary rounded-pill">
                {summaries[game] !== undefined ? `${summaries[game]} draws` : 'Loading...'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
