
import React from 'react';

const GameSelector = ({ games, onGameSelect }) => {
  return (
    <select onChange={(e) => onGameSelect(e.target.value)}>
      <option value="">Select a game</option>
      {games.map((game) => (
        <option key={game.id} value={game.id}>
          {game.name}
        </option>
      ))}
    </select>
  );
};

export default GameSelector;
