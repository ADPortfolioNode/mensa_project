import React, { useState } from 'react';
import Dashboard from './components/Dashboard';
import StartupProgress from './components/StartupProgress';
import Header from './components/Header';

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
      <Header />
      <Dashboard />
    </div>
  );
}
