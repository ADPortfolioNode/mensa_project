import React from 'react';

/**
 * ProgressiveProgressBar Component
 * Shows progress with detailed metadata including:
 * - Current/Total counts
 * - Percentage
 * - Rate (items/sec)
 * - ETA (estimated time remaining)
 * - Status (active/completed/error)
 */
export default function ProgressiveProgressBar({
  current = 0,
  total = 100,
  status = 'idle', // idle, active, completed, error
  label = 'Progress',
  labelColor = null,
  showMetadata = true,
  rate = null, // items per second
  startTime = null, // timestamp when started
  colorScheme = 'primary' // primary, success, warning, danger
}) {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0;
  
  // Calculate rate if not provided
  let calculatedRate = rate;
  let eta = null;
  
  if (startTime && current > 0 && total > 0) {
    const elapsed = (Date.now() - startTime) / 1000; // seconds
    calculatedRate = calculatedRate || (current / elapsed);
    const remaining = total - current;
    eta = remaining / calculatedRate; // seconds
  }

  // Format ETA
  const formatETA = (seconds) => {
    if (!seconds || seconds <= 0) return 'calculating...';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
  };

  // Format rate
  const formatRate = (r) => {
    if (!r || r <= 0) return '0';
    if (r < 1) return r.toFixed(2);
    if (r < 100) return r.toFixed(1);
    return Math.round(r).toLocaleString();
  };

  // Determine color based on status
  const getBarColor = () => {
    switch (status) {
      case 'completed': return 'bg-success';
      case 'error': return 'bg-danger';
      case 'active': return `bg-${colorScheme}`;
      default: return 'bg-secondary';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'completed': return '✓';
      case 'error': return '✗';
      case 'active': return '⟳';
      default: return '○';
    }
  };

  return (
    <div style={{ marginBottom: '16px' }}>
      {/* Header with label and status */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '6px'
      }}>
        <span style={{ fontWeight: '600', fontSize: '14px', color: labelColor || undefined }}>
          {getStatusIcon()} {label}
        </span>
        <span style={{ fontSize: '13px', color: '#6c757d' }}>
          {percentage}%
        </span>
      </div>

      {/* Progress Bar */}
      <div style={{
        width: '100%',
        backgroundColor: '#e9ecef',
        borderRadius: '8px',
        overflow: 'hidden',
        height: '24px',
        boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.1)'
      }}>
        <div 
          className={`${getBarColor()} ${status === 'active' ? 'progress-bar-striped progress-bar-animated' : ''}`}
          style={{
            width: `${percentage}%`,
            height: '100%',
            transition: 'width 0.3s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontWeight: 'bold',
            fontSize: '11px',
            textShadow: '0 1px 2px rgba(0,0,0,0.3)'
          }}
        >
          {percentage > 15 && `${percentage}%`}
        </div>
      </div>

      {/* Metadata */}
      {showMetadata && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginTop: '6px',
          fontSize: '12px',
          color: '#6c757d',
          flexWrap: 'wrap',
          gap: '8px'
        }}>
          <div>
            <strong>Items:</strong> {current.toLocaleString()} / {total.toLocaleString()}
          </div>
          {calculatedRate && status === 'active' && (
            <>
              <div>
                <strong>Rate:</strong> {formatRate(calculatedRate)}/s
              </div>
              {eta && (
                <div>
                  <strong>ETA:</strong> {formatETA(eta)}
                </div>
              )}
            </>
          )}
          {status === 'completed' && startTime && (
            <div>
              <strong>Duration:</strong> {formatETA((Date.now() - startTime) / 1000)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
