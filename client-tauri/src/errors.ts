/** Normalize Tauri/Rust invoke errors for UI (strip noisy prefixes when present). */
export function formatUserFacingError(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err);
  if (!raw.trim()) {
    return "Something went wrong. Try again.";
  }
  // e.g. "invalid args `api_create_user` …" or "…: Email already registered"
  const colon = raw.lastIndexOf(": ");
  if (colon >= 0 && colon < raw.length - 2) {
    const tail = raw.slice(colon + 2).trim();
    if (tail.length >= 3) {
      return tail;
    }
  }
  return raw.trim();
}
