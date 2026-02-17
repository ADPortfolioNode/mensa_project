import React, { useState } from 'react';
import axios from 'axios';
import getApiBase from '../utils/apiBase';
import GamePrediction from './GamePrediction';
import AllPredictionsPanel from './AllPredictionsPanel';

const ALL_GAMES_VALUE = '__all_games__';

export default function PredictionPanel({ games = [], disabled = false }) {
  const [selectedGame, setSelectedGame] = useState(games.length > 0 ? games[0] : '');
  const [recentK, setRecentK] = useState(10);
  const [loadingAll, setLoadingAll] = useState(false);
  const [allPredictions, setAllPredictions] = useState([]);
  const [allError, setAllError] = useState('');

  React.useEffect(() => {
    if (games.length > 0) {
      setSelectedGame(games[0]);
    }
  }, [games]);

  const predictAllGamesConcurrently = async () => {
    if (!games.length) return;

    setLoadingAll(true);
    setAllError('');
    setAllPredictions([]);

    try {
      const apiBase = getApiBase();
      const settled = await Promise.allSettled(
        games.map((game) =>
          axios.post(`${apiBase}/api/predict`, {
            game,
            recent_k: parseInt(recentK, 10),
          })
        )
      );

      const normalized = settled.map((entry, index) => {
        const game = games[index];
        if (entry.status === 'fulfilled') {
          const payload = entry.value?.data || {};
          if (payload?.status === 'error' || payload?.error) {
            return {
              game,
              status: 'error',
              message: payload?.message || payload?.error || 'Prediction failed.',
              prediction: null,
            };
          }
          return {
            game,
            status: 'success',
            message: '',
            prediction: payload,
          };
        }

        return {
          game,
          status: 'error',
          message: entry.reason?.response?.data?.detail || entry.reason?.message || 'Prediction request failed.',
          prediction: null,
        };
      });

      setAllPredictions(normalized);

      const failedCount = normalized.filter((item) => item.status === 'error').length;
      if (failedCount === normalized.length) {
        setAllError('All game predictions failed. Check backend status and trained models.');
      } else if (failedCount > 0) {
        setAllError(`${failedCount} game prediction(s) failed. Showing successful results.`);
      }
    } catch (error) {
      setAllError(error?.message || 'Failed to run all-game predictions.');
    } finally {
      setLoadingAll(false);
    }
  };

  return (
<<<<<<< HEAD
    <>
      {disabled ? (
        <div className="alert alert-warning mb-0">
          <strong>Prediction unavailable:</strong> Train a model first for the selected game.
=======
    <div className="card p-3 mb-3">
      <h5>Predictions</h5>
      {disabled && (
        <div className="alert alert-warning mb-3">
          <strong>Heads up:</strong> No completed training experiment is currently recorded. You can still select a game and try prediction.
>>>>>>> 165dff8cc451c862093412a10d4f2db017f0a8f6
        </div>
      )}
      {games.length > 0 ? (
        <>
          <select className="form-select mb-3" value={selectedGame} onChange={e => setSelectedGame(e.target.value)}>
            <option value={ALL_GAMES_VALUE}>All Games (Concurrent)</option>
            {games.map(game => (
              <option key={game} value={game}>{game}</option>
            ))}
          </select>

          {selectedGame === ALL_GAMES_VALUE ? (
            <div className="card p-3 mb-3">
              <h5>Prediction for All Games</h5>
              <p>Runs one prediction request per game concurrently.</p>
              <div className="input-group mb-2">
                <input
                  type="number"
                  className="form-control"
                  value={recentK}
                  onChange={(e) => setRecentK(e.target.value)}
                  disabled={loadingAll}
                  min="1"
                />
                <button className="btn btn-success" onClick={predictAllGamesConcurrently} disabled={loadingAll}>
                  {loadingAll ? 'Running...' : 'Predict All Games'}
                </button>
              </div>

              {loadingAll && (
                <div className="progress">
                  <div className="progress-bar progress-bar-striped progress-bar-animated w-100" role="progressbar"></div>
                </div>
              )}

              {allError && !loadingAll && (
                <div className="alert alert-warning mt-3 mb-0">
                  <strong>Notice:</strong> {allError}
                </div>
              )}
            </div>
          ) : (
            selectedGame && <GamePrediction game={selectedGame} />
          )}

          {selectedGame === ALL_GAMES_VALUE && allPredictions.length > 0 && (
            <AllPredictionsPanel predictions={allPredictions} />
          )}
        </>
      ) : (
        <p>No games available for prediction.</p>
      )}
    </>
  );
}
