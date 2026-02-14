
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Header = () => {
  const [startupStatus, setStartupStatus] = useState(null);
  const [showProgress, setShowProgress] = useState(true);

  useEffect(() => {
    const pollStartupStatus = async () => {
      try {
        const { getApiBase } = await import('../utils/apiBase');
        const response = await axios.get(`${getApiBase()}/api/startup_status`);
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
        <div style={{
          background: 'linear-gradient(180deg, rgba(18, 27, 58, 0.95), rgba(12, 20, 44, 0.95))',
          borderBottom: '1px solid rgba(110, 168, 254, 0.45)',
          padding: '10px 0',
          marginBottom: '10px',
          boxShadow: '0 4px 14px rgba(6, 12, 28, 0.45)'
        }}>
          <div className="container">
            <div style={{ fontSize: '12px', marginBottom: '6px', color: 'var(--text-secondary)', letterSpacing: '0.2px' }}>
              <strong>🎰 Lottery Data Initialization</strong>
              {startupStatus.current_game && (
                <span style={{ marginLeft: '8px' }}>
                  • {startupStatus.current_game.toUpperCase()}
                  {startupStatus.progress && (
                    <span> ({startupStatus.progress.toFixed(1)}/{startupStatus.total})</span>
                  )}
                </span>
              )}
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
