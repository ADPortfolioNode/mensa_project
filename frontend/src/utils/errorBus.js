const listeners = new Set();

export function publish(errorContext) {
  const payload = {
    timestamp: Date.now(),
    ...errorContext
  };
  listeners.forEach((listener) => listener(payload));
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
