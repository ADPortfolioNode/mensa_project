
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
          backgroundColor: '#f8f9fa',
          borderBottom: '2px solid #dee2e6',
          padding: '12px 0',
          marginBottom: '12px'
        }}>
          <div className="container">
            <div style={{ fontSize: '12px', marginBottom: '6px', color: '#666' }}>
              <strong>🎰 Lottery Data Initialization</strong>
              {startupStatus.current_game && (
                <span style={{ marginLeft: '8px' }}>
                  • {startupStatus.current_game.toUpperCase()}
                  {startupStatus.progress && (
                    <span> ({startupStatus.progress.toFixed(1)}/{startupStatus.total})</span>
                  )}
                </span>
              )}
              {isCompleted && <span style={{ marginLeft: '8px', color: '#28a745' }}>✓ Complete</span>}
            </div>
            <div style={{
              width: '100%',
              backgroundColor: '#e9ecef',
              borderRadius: '4px',
              height: '6px',
              overflow: 'hidden',
              position: 'relative'
            }}>
              <div style={{
                width: `${progressPercentage}%`,
                backgroundColor: isCompleted ? '#28a745' : '#007bff',
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
          <h4>Welcome to Mensa Predictive Dashboard</h4>
          <p>Use this app to predict lottery numbers. Follow the workflow: 1. Ingest data, 2. Train the model, 3. Make predictions.</p>
        </div>
        <h2>Mensa Predictive Dashboard</h2>
      </div>
    </div>
  );
};

export default Header;
