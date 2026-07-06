/** Normalize API timestamps (Unix seconds or ms) for JavaScript Date. */
export function parseTimestampMs(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n < 1e12 ? n * 1000 : n;
}

function parseExperimentIdTimestampMs(experimentId) {
  const match = String(experimentId || '').match(/-(\d{10,})$/);
  if (!match) return null;
  return parseTimestampMs(Number(match[1]));
}

/** Resolve an experiment record to runtime milliseconds. */
export function parseExperimentTimestampMs(record) {
  if (!record) return null;

  if (record.timestamp_iso) {
    const fromIso = new Date(record.timestamp_iso).getTime();
    if (Number.isFinite(fromIso) && fromIso > 0) return fromIso;
  }

  const fromField = parseTimestampMs(record.timestamp ?? record.timestamp_seconds);
  if (fromField != null) return fromField;

  return parseExperimentIdTimestampMs(record.experiment_id);
}

export function formatTimestamp(value, recordOrOptions) {
  const record = recordOrOptions && typeof recordOrOptions === 'object'
    && ('experiment_id' in recordOrOptions || 'timestamp_iso' in recordOrOptions)
    ? recordOrOptions
    : null;
  const localeOptions = record ? undefined : recordOrOptions;

  const ms = record ? parseExperimentTimestampMs(record) : parseTimestampMs(value);
  if (ms == null) return 'N/A';
  return new Date(ms).toLocaleString(undefined, localeOptions);
}

export function formatExperimentTimestamp(record) {
  return formatTimestamp(null, record);
}