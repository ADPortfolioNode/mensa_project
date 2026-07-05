import React from 'react';
import { formatNextGameDateLabel } from '../utils/suggestionUtils';

export default function NextGameScheduleBanner({ prediction, includeDrawCount = true, includeGame = false }) {
  const label = formatNextGameDateLabel(prediction, { includeDrawCount, includeGame });
  if (!label) {
    return null;
  }

  return (
    <div className="prediction-schedule-banner" role="status">
      <span className="prediction-schedule-label">{label}</span>
    </div>
  );
}