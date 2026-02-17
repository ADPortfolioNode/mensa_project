import React, { useState } from 'react';
import Dashboard from './components/Dashboard';
import StartupProgress from './components/StartupProgress';
import Header from './components/Header';
import './styles/modern.css';
import './App.css';

export default function App() {
  const [startupComplete, setStartupComplete] = useState(false);

  const handleStartupComplete = () => {
    setStartupComplete(true);
  };

  return (
    <div className="star-trek-app min-vh-100 py-3 py-md-4">
      {!startupComplete ? (
        <StartupProgress onComplete={handleStartupComplete} />
      ) : (
        <div className="container py-2 py-md-3">
          <Header />
          <Dashboard />
        </div>
      )}
    </div>
  );
}
