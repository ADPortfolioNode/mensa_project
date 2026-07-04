/**
 * setTimeout-based poller that avoids request pile-up from setInterval.
 * - Skips ticks while a request is in-flight
 * - Backs off on network errors
 * - Pauses when the browser tab is hidden
 */
export function isNetworkError(error) {
  return !error?.response;
}

export function startPolling({
  tick,
  intervalMs = 5000,
  maxBackoffMs = 30000,
  pauseWhenHidden = true,
  shouldStop,
}) {
  let timeoutId = null;
  let stopped = false;
  let inFlight = false;
  let consecutiveErrors = 0;

  const schedule = (delay) => {
    if (stopped) return;
    clearTimeout(timeoutId);
    timeoutId = setTimeout(runTick, delay);
  };

  const runTick = async () => {
    if (stopped) return;

    if (pauseWhenHidden && typeof document !== 'undefined' && document.hidden) {
      schedule(intervalMs);
      return;
    }

    if (inFlight) {
      schedule(intervalMs);
      return;
    }

    inFlight = true;
    try {
      const result = await tick();
      consecutiveErrors = 0;
      if (shouldStop?.(result)) {
        stop();
        return;
      }
      schedule(intervalMs);
    } catch (error) {
      if (isNetworkError(error)) {
        consecutiveErrors += 1;
        const backoff = Math.min(
          maxBackoffMs,
          intervalMs * (2 ** Math.min(consecutiveErrors, 4)),
        );
        schedule(backoff);
      } else {
        schedule(intervalMs);
      }
    } finally {
      inFlight = false;
    }
  };

  const stop = () => {
    stopped = true;
    clearTimeout(timeoutId);
  };

  schedule(0);
  return stop;
}