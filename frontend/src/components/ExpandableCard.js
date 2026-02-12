import React, { useState } from 'react';

/**
 * ExpandableCard Component
 * Provides a card that can expand to full width (2 columns) when active
 * Shows metadata and details when expanded
 */
export default function ExpandableCard({ 
  title, 
  children, 
  metadata = {},
  statusBadge,
  isActive = false,
  onToggle,
  className = "",
  neonBorder = false 
}) {
  const [expanded, setExpanded] = useState(false);

  const handleToggle = () => {
    const newState = !expanded;
    setExpanded(newState);
    if (onToggle) {
      onToggle(newState);
    }
  };

  const cardClasses = `card p-3 mb-3 h-100 shadow-lg ${neonBorder ? 'border-neon' : ''} ${className}`;
  const headerClasses = expanded ? 'bg-primary text-white' : '';

  return (
    <div className={cardClasses} style={{ 
      transition: 'all 0.3s ease',
      position: 'relative'
    }}>
      <div className={`card-header ${headerClasses}`} style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        cursor: 'pointer',
        padding: '12px 16px',
        borderRadius: expanded ? '8px 8px 0 0' : '0'
      }} onClick={handleToggle}>
        <h5 className={`${neonBorder ? 'text-neon' : ''}`} style={{ margin: 0 }}>
          {title}
        </h5>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {statusBadge && <span>{statusBadge}</span>}
          {isActive && (
            <span className="badge bg-warning text-dark">
              Active
            </span>
          )}
          <button 
            className="btn btn-sm btn-outline-secondary"
            onClick={(e) => { e.stopPropagation(); handleToggle(); }}
            style={{ padding: '2px 8px', fontSize: '12px' }}
          >
            {expanded ? '▼' : '▶'}
          </button>
        </div>
      </div>

      <div className="card-body" style={{ padding: '16px' }}>
        {expanded && Object.keys(metadata).length > 0 && (
          <div style={{
            background: '#f8f9fa',
            padding: '12px',
            borderRadius: '6px',
            marginBottom: '12px',
            border: '1px solid #dee2e6'
          }}>
            <h6 style={{ marginBottom: '8px', color: '#495057' }}>Metadata</h6>
            <div style={{ fontSize: '13px' }}>
              {Object.entries(metadata).map(([key, value]) => (
                <div key={key} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between',
                  padding: '4px 0',
                  borderBottom: '1px solid #e9ecef'
                }}>
                  <span style={{ fontWeight: '500', color: '#6c757d' }}>{key}:</span>
                  <span style={{ color: '#212529' }}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {children}
      </div>
    </div>
  );
}
