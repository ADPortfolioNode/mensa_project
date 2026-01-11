import React, { useState } from 'react';
import Dashboard from './components/Dashboard';
import StartupProgress from './components/StartupProgress';

export default function App() {
  const [startupComplete, setStartupComplete] = useState(false);

  const handleStartupComplete = () => {
    setStartupComplete(true);
  };

  if (!startupComplete) {
    return <StartupProgress onComplete={handleStartupComplete} />;
  }

  return (
    <div className="container py-4">
      <div className="alert alert-info">
        <h4>Welcome to Mensa Predictive Dashboard</h4>
        <p>Use this app to predict lottery numbers. Follow the workflow: 1. Ingest data, 2. Train the model, 3. Make predictions.</p>
      </div>
      <h2>Mensa Predictive Dashboard</h2>
      <Dashboard />
    </div>
  );
}
