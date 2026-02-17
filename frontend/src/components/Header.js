
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
<<<<<<< HEAD
        <div className="header-startup-strip py-2 mb-3">
          <div className="container">
            <div className="header-startup-meta small mb-2">
=======
        <div style={{
          background: 'linear-gradient(180deg, rgba(18, 27, 58, 0.95), rgba(12, 20, 44, 0.95))',
          borderBottom: '1px solid rgba(110, 168, 254, 0.45)',
          padding: '10px 0',
          marginBottom: '10px',
          boxShadow: '0 4px 14px rgba(6, 12, 28, 0.45)'
        }}>
          <div className="container">
            <div style={{ fontSize: '12px', marginBottom: '6px', color: 'var(--text-secondary)', letterSpacing: '0.2px' }}>
>>>>>>> 165dff8cc451c862093412a10d4f2db017f0a8f6
              <strong>🎰 Lottery Data Initialization</strong>
              {startupStatus.current_game && (
                <span className="ms-2">
                  • {startupStatus.current_game.toUpperCase()}
                  {startupStatus.progress && (
                    <span> ({startupStatus.progress.toFixed(1)}/{startupStatus.total})</span>
                  )}
                </span>
              )}
<<<<<<< HEAD
              {isCompleted && <span className="ms-2 text-success">✓ Complete</span>}
            </div>
            <div className="progress header-startup-progress" role="progressbar" aria-valuenow={progressPercentage} aria-valuemin="0" aria-valuemax="100">
              <progress
                className={`header-startup-progress-native ${isCompleted ? 'is-complete' : isIngesting ? 'is-active' : 'is-idle'}`}
                value={Math.max(0, Math.min(progressPercentage, 100))}
                max="100"
              />
=======
              {isCompleted && <span style={{ marginLeft: '8px', color: '#8affd2' }}>✓ Complete</span>}
            </div>
            <div style={{
              width: '100%',
              backgroundColor: 'rgba(26, 40, 80, 0.95)',
              border: '1px solid rgba(110, 168, 254, 0.35)',
              borderRadius: '4px',
              height: '6px',
              overflow: 'hidden',
              position: 'relative'
            }}>
              <div style={{
                width: `${progressPercentage}%`,
                background: isCompleted
                  ? 'linear-gradient(90deg, rgba(111, 255, 188, 0.95), rgba(84, 220, 170, 0.95))'
                  : 'linear-gradient(90deg, var(--accent-green-dark), var(--accent-green), var(--accent-green-light))',
                height: '100%',
                transition: 'width 0.3s ease',
                borderRadius: '4px'
              }} />
>>>>>>> 165dff8cc451c862093412a10d4f2db017f0a8f6
            </div>
          </div>
        </div>
      )}

      {/* Main Header */}
      <div className="container py-4">
        <div className="alert alert-info">
          <h4 style={{ marginBottom: '0.4rem', letterSpacing: '0.3px' }}>Welcome to Mensa Predictive Dashboard</h4>
          <p style={{ marginBottom: 0 }}>Use this app to predict lottery numbers. Follow the workflow: 1. Ingest data, 2. Train the model, 3. Make predictions.</p>
        </div>
        <h2 style={{ marginTop: '0.2rem', marginBottom: 0, letterSpacing: '0.25px' }}>Mensa Predictive Dashboard</h2>
      </div>
    </div>
  );
};

export default Header;
