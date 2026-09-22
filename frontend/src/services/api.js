// Prompt Guard - API service
//
// This is the ONLY file that talks to the backend, per the handoff doc
// (section 13.11: "Keep all API calls in one file such as src/services/api.js").
//
// Contract (must not change without all three teammates agreeing):
//   POST /scan
//   Request:  { "prompt": "USER PROMPT HERE" }
//   Response: {
//     scan_id, original_prompt, sanitized_prompt, risk_score, decision,
//     threats, signals, pii, timestamp
//   }

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, { status, cause } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.cause = cause;
  }
}

/**
 * Send a prompt to the backend for scanning.
 * @param {string} prompt
 * @returns {Promise<import('./types').ScanResult>}
 */
export async function scanPrompt(prompt) {
  let response;
  try {
    response = await fetch(`${BASE_URL}/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
  } catch (err) {
    // Network failure - backend unreachable, CORS issue, offline, etc.
    throw new ApiError(
      "Can't reach the Prompt Guard backend. Is it running on " + BASE_URL + "?",
      { cause: err }
    );
  }

  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      detail = body?.detail || body?.message || "";
    } catch {
      // response wasn't JSON - ignore
    }
    throw new ApiError(
      detail || `Scan failed (HTTP ${response.status}).`,
      { status: response.status }
    );
  }

  return response.json();
}

export { BASE_URL };
