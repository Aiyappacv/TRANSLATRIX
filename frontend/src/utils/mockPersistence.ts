export function loadMockState<T>(key: string, fallback: T): T {
  if (typeof window === "undefined" || !window.localStorage) return structuredClone(fallback);
  try {
    const stored = window.localStorage.getItem(key);
    return stored ? JSON.parse(stored) as T : structuredClone(fallback);
  } catch {
    return structuredClone(fallback);
  }
}

export function saveMockState<T>(key: string, value: T): void {
  if (typeof window === "undefined" || !window.localStorage) return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Mock persistence is best-effort and must never block the UI.
  }
}
