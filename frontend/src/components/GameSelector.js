
import React from 'react';


const GameSelector = ({ games, onGameSelect }) => {
  // Support both string and object game lists
  const isObjectList = games.length > 0 && typeof games[0] === 'object';
  return (
    <select className="form-select mb-2" onChange={(e) => onGameSelect(e.target.value)}>
      <option value="">Select a game</option>
      {games.map((game) => (
        isObjectList ? (
          <option key={game.id || game.name || game} value={game.id || game.name || game}>
            {game.name || game.id || game}
          </option>
        ) : (
          <option key={game} value={game}>{game}</option>
        )
      ))}
    </select>
  );
};

export default GameSelector;
