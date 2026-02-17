import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import getApiBase from '../utils/apiBase';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export default function GameSummaryPanel({ games, refreshKey = 0, initialSummaries = {} }) {
  const [summaries, setSummaries] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const API_BASE = useMemo(() => getApiBase(), []);

  useEffect(() => {
    let isMounted = true;
    if (games && games.length > 0) {
      fetchSummaries(isMounted);
    } else {
      setSummaries({});
    }
    return () => { isMounted = false; };
  }, [games, API_BASE, refreshKey, initialSummaries]);

  useEffect(() => {
    if (initialSummaries && Object.keys(initialSummaries).length > 0) {
      setSummaries((prev) => ({ ...initialSummaries, ...prev }));
    }
  }, [initialSummaries]);

  const fetchGameSummaryWithRetry = async (game, maxAttempts = 3) => {
    let lastError = null;
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      try {
        const response = await axios.get(`${API_BASE}/api/games/${game}/summary`, { timeout: 12000 });
        return response.data.draw_count;
      } catch (e) {
        lastError = e;
        if (attempt < maxAttempts) {
          await sleep(attempt * 600);
        }
      }
    }
    throw lastError;
  };

  const fetchSummaries = async (isMounted = true) => {
    if (!isMounted) return;
    setLoading(true);
    setError(null);
    const newSummaries = { ...initialSummaries };
    let failedCount = 0;

    for (const game of games) {
      try {
        const drawCount = await fetchGameSummaryWithRetry(game);
        if (isMounted) {
          newSummaries[game] = drawCount;
        }
      } catch (e) {
        console.error(`Failed to fetch summary for ${game}:`, e);
        failedCount += 1;
        if (isMounted) {
          if (newSummaries[game] === undefined) {
            newSummaries[game] = 0;
          }
        }
      }
    }

    if (isMounted) {
      setSummaries(newSummaries);
      if (failedCount === games.length && games.length > 0) {
        setError('Failed to fetch game summaries. Backend may still be warming up.');
      } else if (failedCount > 0) {
        setError('Some game summaries are delayed. Showing latest available values.');
      }
      setLoading(false);
    }
  };

  return (
    <div className="card p-3 mb-3">
      <h5>Game Contents</h5>
      {loading && (
        <div className="progress mb-2">
          <div className="progress-bar progress-bar-striped progress-bar-animated w-100" role="progressbar"></div>
        </div>
      )}
      {error && !loading && (
        <div className="alert alert-warning">
          <strong>Warning:</strong> {error}
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
