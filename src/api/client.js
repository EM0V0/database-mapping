/**
 * HTTP helpers for Flask REST endpoints resolved against optional env overrides.
 *
 * When VUE_APP_API_ORIGIN is empty, requests stay same-origin (/api/*) so the webpack
 * proxy can forward traffic to Flask during npm run serve.
 */

const ORIGIN = (process.env.VUE_APP_API_ORIGIN || '').trim().replace(/\/$/, '');

/**
 * Builds an absolute or relative REST URL.
 *
 * @param {string} path path beginning with '/', e.g. '/api/health'
 * @returns {string}
 */
export function apiUrl(path) {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return ORIGIN ? `${ORIGIN}${normalized}` : normalized;
}

/**
 * Lightweight JSON-aware fetch helper for JSON request bodies/responses.
 *
 * @param {string} path
 * @param {RequestInit} [init]
 * @returns {Promise<any>}
 */
export async function fetchJson(path, init = {}) {
  const response = await fetch(apiUrl(path), init);
  const text = await response.text();
  let payload;

  try {
    payload = text ? JSON.parse(text) : null;
  } catch (error) {
    throw new Error(`Non-JSON response (${response.status}): ${text.slice(0, 200)}`);
  }

  if (!response.ok) {
    const message = (payload && payload.error) ? payload.error : `${response.status} ${response.statusText}`;
    throw new Error(message);
  }

  return payload;
}

/**
 * Multipart uploads that still deserialize JSON payloads from the Flask API.
 *
 * @param {string} path
 * @param {FormData} formData
 * @returns {Promise<any>}
 */
export async function postForm(path, formData) {
  const response = await fetch(apiUrl(path), {
    method: 'POST',
    body: formData,
  });

  const text = await response.text();
  let payload;

  try {
    payload = text ? JSON.parse(text) : null;
  } catch (error) {
    throw new Error(`Non-JSON response (${response.status}): ${text.slice(0, 200)}`);
  }

  if (!response.ok) {
    const message = (payload && payload.error) ? payload.error : `${response.status} ${response.statusText}`;
    throw new Error(message);
  }

  return payload;
}
