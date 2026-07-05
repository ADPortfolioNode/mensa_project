/** Shared training payload + result formatting for Mensa dashboards. */

export const BASE_MODEL_TYPE = 'Random Forest Regressor';

const STRATEGY_LABELS = {
  single: 'Single model',
  ensemble: 'Blended with prior model',
  ensemble_top3: 'Top-3 ensemble',
};

export function formatModelStrategyLabel(strategy) {
  if (!strategy) return null;
  const key = String(strategy).toLowerCase();
  return STRATEGY_LABELS[key] || String(strategy);
}

/** Human-readable Model Type line for dashboard metadata. */
export function formatModelTypeLabel({ strategy, blendWeight } = {}) {
  const strategyLabel = formatModelStrategyLabel(strategy);
  if (!strategyLabel) return BASE_MODEL_TYPE;
  if (strategy === 'ensemble' && blendWeight != null && Number.isFinite(Number(blendWeight))) {
    return `${BASE_MODEL_TYPE} (${strategyLabel}, weight ${Number(blendWeight).toFixed(2)})`;
  }
  return `${BASE_MODEL_TYPE} (${strategyLabel})`;
}

export function clampTrainValue(value, min, max, fallback) {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, n));
}

/** train_size must be a 0.1–0.5 fraction; tolerate legacy percent inputs (e.g. 25 or 254). */
export function normalizeTrainSizeFraction(value, fallback = 0.25) {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  const asFraction = n > 1 ? n / 100 : n;
  return clampTrainValue(asFraction, 0.1, 0.5, fallback);
}

export function formatTrainSizePercent(testSize) {
  return `${Math.round(normalizeTrainSizeFraction(testSize) * 100)}%`;
}

export function normalizeNEstimators(value, fallback = 250) {
  return Math.round(clampTrainValue(value, 50, 600, fallback));
}

export function normalizeMaxDepth(value, fallback = 18) {
  return Math.round(clampTrainValue(value, 4, 32, fallback));
}

export function normalizeMaxIterations(value, fallback = 40) {
  return Math.round(clampTrainValue(value, 1, 100, fallback));
}

export function buildTrainRequestBody(game, trainParams) {
  const trainingTarget = clampTrainValue(trainParams.targetAccuracy ?? 0.9, 0.5, 0.99, 0.9);
  const body = {
    game,
    target_accuracy: trainingTarget,
    max_iterations: normalizeMaxIterations(trainParams.maxIterations, 40),
    train_size: normalizeTrainSizeFraction(trainParams.testSize, 0.25),
    n_estimators: normalizeNEstimators(trainParams.nEstimators, 250),
    max_depth: normalizeMaxDepth(trainParams.maxDepth, 18),
    random_state: Math.round(clampTrainValue(trainParams.randomState, 0, 2_147_483_647, 42)),
    window_size: Math.round(clampTrainValue(trainParams.windowSize, 1, 8, 3)),
    auto_tune: Boolean(trainParams.autoTune ?? true),
  };
  if (trainParams.blendStep != null && Number.isFinite(Number(trainParams.blendStep))) {
    body.blend_step = clampTrainValue(trainParams.blendStep, 0.01, 0.5, 0.05);
  }
  return body;
}

export function formatTrainingSuccessMessage(game, data) {
  const recordScore = data.record_accuracy ?? data.highest_accuracy ?? data.baseline_accuracy;
  const trainScore = recordScore ?? data.score ?? data.accuracy ?? data.final_accuracy;
  const scoreText = trainScore != null ? `${(Number(trainScore) * 100).toFixed(2)}%` : 'N/A';
  const strategy = data.model_strategy;
  const prevAcc = data.previous_accuracy ?? data.baseline_accuracy ?? recordScore;
  const candAcc = data.candidate_accuracy ?? data.new_accuracy;
  const trainTarget = data.training_target ?? data.target_accuracy;
  let learningNote = '';
  if (data.retained_previous_model && recordScore != null && candAcc != null) {
    learningNote = ` Record ${(Number(recordScore) * 100).toFixed(2)}% kept (new run ${(Number(candAcc) * 100).toFixed(2)}% did not beat the floor).`;
  } else if (data.retained_previous_model && prevAcc != null && candAcc != null) {
    learningNote = ` Record ${(Number(prevAcc) * 100).toFixed(2)}% kept (new run ${(Number(candAcc) * 100).toFixed(2)}%).`;
  } else if (strategy === 'ensemble' && data.blend_weight != null) {
    learningNote = ` Ensemble blend (weight ${Number(data.blend_weight).toFixed(2)}) improved on prior model.`;
  } else if (prevAcc != null && trainScore != null && trainScore > prevAcc) {
    learningNote = ` Improved from prior ${(prevAcc * 100).toFixed(2)}%.`;
  }
  const targetNote = trainTarget != null ? ` Target: ${(Number(trainTarget) * 100).toFixed(2)}%.` : '';
  return `Training completed successfully for ${String(game).toUpperCase()}! Experiment ID: ${data.experiment_id}, Accuracy: ${scoreText}.${targetNote}${learningNote}`;
}

export function isTrainSuccessStatus(status) {
  const normalized = String(status || '').toLowerCase();
  return normalized === 'completed' || normalized === 'success';
}

/** User-facing training failure text for gateway/proxy failures during long training. */
export function formatTrainingErrorMessage(error, formatApiError) {
  const status = error?.response?.status;
  const base = formatApiError(error, 'Training request failed.');
  if (status === 502 || status === 503 || /502 bad gateway/i.test(base) || /503 service unavailable/i.test(base)) {
    return (
      'Backend unavailable during training (HTTP '
      + (status || '502')
      + '). The API container may have restarted or run out of memory on large games like Powerball. '
      + 'Wait 30s, check docker logs for mensa_backend, then retry with Target Accuracy 85% to 90%, '
      + 'Max Iterations 10 to 12, N Estimators 150, and Auto-tune off. '
      + 'Also confirm a completed experiment was not already saved.'
    );
  }
  if (status === 504 || /504 gateway timeout/i.test(base) || /timeout/i.test(base)) {
    return (
      'Gateway timeout while waiting for training to finish. Training can take several minutes — '
      + 'the job may still be running on the server. Check Completed Training Experiments in a minute, '
      + 'or retry with fewer Max Iterations / disable Auto-tune train split.'
    );
  }
  return base;
}