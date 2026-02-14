import React, { memo, useMemo } from 'react';

export function normalizeProgress(current, total) {
  const safeTotal = Number(total) > 0 ? Number(total) : 0;
  const safeCurrent = Number(current) > 0 ? Number(current) : 0;
  const rawPercentage = safeTotal > 0 ? (safeCurrent / safeTotal) * 100 : 0;
  const clampedPercentage = Math.max(0, Math.min(100, rawPercentage));

  return {
    safeCurrent,
    safeTotal,
    clampedPercentage,
  };
}

function formatETA(seconds) {
  if (!seconds || seconds <= 0) return 'calculating...';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${Math.round(seconds / 3600)}h`;
}

function formatRate(rateValue) {
  if (!rateValue || rateValue <= 0) return '0';
  if (rateValue < 1) return rateValue.toFixed(2);
  if (rateValue < 100) return rateValue.toFixed(1);
  return Math.round(rateValue).toLocaleString();
}

function getBarColor(status, colorScheme) {
  switch (status) {
    case 'completed': return 'bg-success';
    case 'error': return 'bg-danger';
    case 'active': return `bg-${colorScheme}`;
    default: return 'bg-secondary';
  }
}

function getFillGradient(status, colorScheme) {
  if (status === 'completed') {
    return 'linear-gradient(90deg, rgba(111, 255, 188, 0.95), rgba(84, 220, 170, 0.95))';
  }
  if (status === 'error') {
    return 'linear-gradient(90deg, rgba(255, 128, 150, 0.92), rgba(235, 87, 120, 0.92))';
  }
  if (status === 'active' && colorScheme === 'warning') {
    return 'linear-gradient(90deg, rgba(255, 196, 120, 0.95), rgba(245, 160, 90, 0.95))';
  }
  return 'linear-gradient(90deg, var(--accent-green-dark), var(--accent-green), var(--accent-green-light))';
}

function getStatusIcon(status) {
  switch (status) {
    case 'completed': return '✓';
    case 'error': return '✗';
    case 'active': return '⟳';
    default: return '○';
  }
}

function ProgressiveProgressBar({
  current = 0,
  total = 100,
  status = 'idle', // idle, active, completed, error
  label = 'Progress',
  labelColor = null,
  showMetadata = true,
  rate = null, // items per second
  startTime = null, // timestamp when started
  colorScheme = 'primary', // primary, success, warning, danger
  indeterminate = false
}) {
  const { safeCurrent, safeTotal, clampedPercentage } = useMemo(
    () => normalizeProgress(current, total),
    [current, total]
  );
  const isIndeterminate = indeterminate && status === 'active';
  const percentageLabel = useMemo(
    () => clampedPercentage.toFixed(status === 'active' ? 1 : 0),
    [clampedPercentage, status]
  );
  
  const { calculatedRate, eta } = useMemo(() => {
    let calculated = rate;
    let etaValue = null;

    if (startTime && safeCurrent > 0 && safeTotal > 0) {
      const elapsed = (Date.now() - startTime) / 1000;
      calculated = calculated || (safeCurrent / Math.max(elapsed, 1));
      const remaining = safeTotal - safeCurrent;
      etaValue = remaining / calculated;
    }

    return { calculatedRate: calculated, eta: etaValue };
  }, [rate, startTime, safeCurrent, safeTotal]);

  const labelTextColor = labelColor || 'var(--text-primary)';
  const subTextColor = 'var(--text-secondary)';
  const trackStyle = {
    width: '100%',
    backgroundColor: 'var(--bg-tertiary)',
    border: '1px solid var(--border-color)',
    borderRadius: '999px',
    overflow: 'hidden',
    height: '24px',
    boxShadow: 'inset 0 0 0 1px rgba(255,255,255,0.04), inset 0 2px 6px rgba(0,0,0,0.25)'
  };
  const fillStyle = {
    width: isIndeterminate ? '100%' : `${clampedPercentage}%`,
    height: '100%',
    transition: 'width 0.25s linear',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#081229',
    fontWeight: 'bold',
    fontSize: '11px',
    textShadow: '0 1px 1px rgba(255,255,255,0.25)',
    willChange: 'width',
    background: getFillGradient(status, colorScheme),
    borderRight: isIndeterminate ? 'none' : '1px solid rgba(255,255,255,0.35)',
    boxShadow: 'inset 0 0 10px rgba(255,255,255,0.18), 0 0 14px rgba(110, 168, 254, 0.25)'
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
        <span style={{ fontWeight: '700', fontSize: '14px', color: labelTextColor, letterSpacing: '0.2px' }}>
          {getStatusIcon(status)} {label}
        </span>
        <span style={{ fontSize: '13px', color: subTextColor }}>
          {isIndeterminate ? 'In progress...' : `${percentageLabel}%`}
        </span>
      </div>

      {/* Progress Bar */}
      <div style={trackStyle}>
        <div 
          className={`${getBarColor(status, colorScheme)} ${status === 'active' ? 'progress-bar-striped progress-bar-animated' : ''}`}
          style={fillStyle}
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(clampedPercentage)}
        >
          {!isIndeterminate && clampedPercentage > 15 && `${percentageLabel}%`}
        </div>
      </div>

      {/* Metadata */}
      {showMetadata && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginTop: '6px',
          fontSize: '12px',
          color: subTextColor,
          flexWrap: 'wrap',
          gap: '8px'
        }}>
          <div>
            <strong>Items:</strong> {safeCurrent.toLocaleString()} / {safeTotal.toLocaleString()}
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

export default memo(ProgressiveProgressBar);
