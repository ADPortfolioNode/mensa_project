import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import Dashboard from './components/Dashboard';
import StartupProgress from './components/StartupProgress';
import Header from './components/Header';
import { publish, subscribe } from './utils/errorBus';

export default function App() {
  const [startupComplete, setStartupComplete] = useState(false);
  const [appError, setAppError] = useState(null);
  const interceptorsSet = useRef(false);

  useEffect(() => {
    const unsubscribe = subscribe(setAppError);
    return unsubscribe;
  }, []);

  useEffect(() => {
    if (interceptorsSet.current) return;
    interceptorsSet.current = true;

    axios.interceptors.response.use(
      (response) => response,
      (error) => {
        publish({
          source: 'axios',
          message: error?.message || 'Request failed',
          detail: error?.response?.data || null
        });
        return Promise.reject(error);
      }
    );
  }, []);

  useEffect(() => {
    const handleError = (event) => {
      publish({
        source: 'window',
        message: event.message || 'Unhandled error',
        detail: event.error || null
      });
    };

    const handleRejection = (event) => {
      publish({
        source: 'promise',
        message: event.reason?.message || 'Unhandled promise rejection',
        detail: event.reason || null
      });
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleRejection);
    };
  }, []);

  const handleStartupComplete = () => {
    setStartupComplete(true);
  };

  if (!startupComplete) {
    return <StartupProgress onComplete={handleStartupComplete} />;
  }

  return (
    <div className="container py-4">
      {appError && (
        <div
          style={{
            background: '#2b1d1d',
            border: '1px solid #ff5c5c',
            color: '#ffd6d6',
            padding: '10px 14px',
            borderRadius: '8px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px'
          }}
        >
          <div style={{ fontSize: '13px' }}>
            <strong>System error:</strong> {appError.message || 'Unexpected error'}
          </div>
          <button
            className="btn btn-sm btn-outline-light"
            onClick={() => setAppError(null)}
            style={{ whiteSpace: 'nowrap' }}
          >
            Dismiss
          </button>
        </div>
      )}
      <Header />
      <Dashboard />
    </div>
  );
}
