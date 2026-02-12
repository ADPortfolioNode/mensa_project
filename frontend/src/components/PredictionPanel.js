import React, { useState } from 'react';
import GamePrediction from './GamePrediction';

export default function PredictionPanel({ games = [] }) {
  const [selectedGame, setSelectedGame] = useState(games.length > 0 ? games[0] : '');

  React.useEffect(() => {
    if (games.length > 0) {
      setSelectedGame(games[0]);
    }
  }, [games]);

  return (
    <div className="card p-3 mb-3">
      <h5>Predictions</h5>
      {games.length > 0 ? (
        <>
          <select className="form-select mb-3" value={selectedGame} onChange={e => setSelectedGame(e.target.value)}>
            <option value="all">All games</option>
            {games.map(game => (
              <option key={game} value={game}>{game}</option>
            ))}
          </select>
          {selectedGame && <GamePrediction game={selectedGame} />}
        </>
      ) : (
        <p>No games available for prediction.</p>
      )}
    </div>
  );
}
