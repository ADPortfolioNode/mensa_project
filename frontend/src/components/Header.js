
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { getApiBase } from '../utils/apiBase';

const Header = () => {
  const [startupStatus, setStartupStatus] = useState(null);
  const [showProgress, setShowProgress] = useState(true);

  const fetchStartupStatus = async () => {
    const apiBase = getApiBase();
    const primaryUrl = `${apiBase}/api/startup_status`;
    const fallbackUrl = apiBase
      ? null
      : `${window.location.protocol}//${window.location.hostname}:5000/api/startup_status`;

    try {
      return await axios.get(primaryUrl, { timeout: 10000 });
    } catch (primaryError) {
      if (!fallbackUrl) throw primaryError;
      return axios.get(fallbackUrl, { timeout: 10000 });
    }
  };

  useEffect(() => {
    const pollStartupStatus = async () => {
      try {
        const response = await fetchStartupStatus();
        setStartupStatus(response.data);
        
        // Hide progress bar after completion
        if (response.data.status === 'completed') {
          setTimeout(() => setShowProgress(false), 500);
        }
      } catch (error) {
        // Silent fail - continue polling
      }
    };

    const interval = setInterval(pollStartupStatus, 2000);
    pollStartupStatus();

    return () => clearInterval(interval);
  }, []);

  const getProgressPercentage = () => {
    if (!startupStatus) return 0;
    const progress = Number(startupStatus.progress || 0);
    const total = Number(startupStatus.total || 1);
    return Math.min((progress / total) * 100, 100);
  };

  const progressPercentage = getProgressPercentage();
  const isIngesting = startupStatus?.status === 'ingesting';
  const isCompleted = startupStatus?.status === 'completed';

  return (
    <div>
      {/* Startup Progress Bar */}
      {showProgress && startupStatus && (
        <div className="header-startup-strip py-2 mb-3">
          <div className="container">
            <div className="header-startup-meta small mb-2">
              <strong>🎰 Lottery Data Initialization</strong>
              {startupStatus.current_game && (
                <span className="ms-2">
                  • {startupStatus.current_game.toUpperCase()}
                  {startupStatus.progress && (
                    <span> ({startupStatus.progress.toFixed(1)}/{startupStatus.total})</span>
                  )}
                </span>
              )}
              {isCompleted && <span className="ms-2 text-success">✓ Complete</span>}
            </div>
            <div className="progress header-startup-progress" role="progressbar" aria-valuenow={progressPercentage} aria-valuemin="0" aria-valuemax="100">
              <progress
                className={`header-startup-progress-native ${isCompleted ? 'is-complete' : isIngesting ? 'is-active' : 'is-idle'}`}
                value={Math.max(0, Math.min(progressPercentage, 100))}
                max="100"
              />
            </div>
          </div>
        </div>
      )}

      {/* Main Header */}
      <div className="container py-4">
        <div className="alert alert-info">
          <h4>Welcome to Mensa Predictive Dashboard</h4>
          <p>Use this app to predict lottery numbers. Follow the workflow: 1. Ingest data, 2. Train the model, 3. Make predictions.</p>
        </div>
        <h2>Mensa Predictive Dashboard</h2>
      </div>
    </div>
  );
};

export default Header;
