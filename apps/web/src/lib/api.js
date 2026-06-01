import { getCookie, setCookie } from './cookies.js';

/**
 * Perform an anonymous join, persist the new credentials to cookies, and
 * return the raw response payload so callers can update their local state.
 *
 * @returns {{ access_token: string, username: string, role: string }}
 */
async function refreshSession() {
  const res = await fetch('/auth/join', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error('Failed to obtain a new session from the server');
  const data = await res.json();
  setCookie('kairo_token', data.access_token);
  setCookie('kairo_username', data.username);
  return data;
}

/**
 * Authenticated fetch with automatic 401 interception.
 *
 * On a 401 response the client transparently obtains a fresh anonymous
 * session (re-join), updates the stored cookies, and retries the original
 * request once.  If the retry also fails the error is propagated to the
 * caller as a plain Error.
 *
 * @param {string} url
 * @param {RequestInit} options
 * @param {(newToken: string, newUsername: string) => void} [onTokenRefreshed]
 * @returns {Promise<Response>}
 */
async function authenticatedFetch(url, options = {}, onTokenRefreshed) {
  let token = getCookie('kairo_token');

  const buildHeaders = (tok) => ({
    ...options.headers,
    Authorization: `Bearer ${tok}`,
  });

  let res = await fetch(url, { ...options, headers: buildHeaders(token) });

  if (res.status === 401) {
    const refreshed = await refreshSession();
    token = refreshed.access_token;
    if (onTokenRefreshed) onTokenRefreshed(refreshed.access_token, refreshed.username);

    res = await fetch(url, { ...options, headers: buildHeaders(token) });
    if (!res.ok) {
      throw new Error(`Request to ${url} failed after session refresh (${res.status})`);
    }
  }

  return res;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Obtain an initial anonymous session.  Only call this when no token cookie
 * exists yet.  For silent re-auth, `authenticatedFetch` handles it internally.
 */
export async function joinServer(onTokenRefreshed) {
  const data = await refreshSession();
  if (onTokenRefreshed) onTokenRefreshed(data.access_token, data.username);
  return data;
}

/**
 * @param {(newToken: string, newUsername: string) => void} [onTokenRefreshed]
 * @returns {Promise<Response>}
 */
export async function fetchRooms(onTokenRefreshed) {
  return authenticatedFetch('/api/rooms', {}, onTokenRefreshed);
}

/**
 * @param {number} roomId
 * @param {(newToken: string, newUsername: string) => void} [onTokenRefreshed]
 * @returns {Promise<object[]>}
 */
export async function fetchMessages(roomId, onTokenRefreshed) {
  const res = await authenticatedFetch(
    `/api/rooms/${roomId}/messages`,
    {},
    onTokenRefreshed,
  );
  if (!res.ok) throw new Error(`Failed to fetch messages for room ${roomId} (${res.status})`);
  return res.json();
}

/**
 * @param {(newToken: string, newUsername: string) => void} [onTokenRefreshed]
 * @returns {Promise<{ username: string, role: string, pfp_urls: object|null }>}
 */
export async function fetchUserProfile(onTokenRefreshed) {
  const res = await authenticatedFetch('/api/users/me', {}, onTokenRefreshed);
  if (!res.ok) throw new Error(`Failed to fetch user profile (${res.status})`);
  return res.json();
}

/**
 * @param {number} roomId
 * @param {(newToken: string, newUsername: string) => void} [onTokenRefreshed]
 * @returns {Promise<Response>}
 */
export async function fetchPresence(roomId, onTokenRefreshed) {
  return authenticatedFetch(`/api/rooms/${roomId}/presence`, {}, onTokenRefreshed);
}

/**
 * Upload a file with XHR so progress events are available.
 * Reads the token from the cookie at call time.
 *
 * @param {File} file
 * @param {number} roomId
 * @param {{ onProgress?: (pct: number) => void }} [opts]
 * @returns {Promise<{ upload_id: string, original_filename: string, mime_type: string, size_bytes: number }>}
 */
export function uploadFile(file, roomId, { onProgress } = {}) {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/api/data/upload/file?room_id=${roomId ?? 0}`);
    xhr.setRequestHeader('Authorization', `Bearer ${getCookie('kairo_token')}`);

    if (onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        let detail = 'Upload failed';
        try { detail = JSON.parse(xhr.responseText).detail || detail; } catch (_) {}
        reject(new Error(detail));
      }
    };

    xhr.onerror = () => reject(new Error('Network error during upload'));
    xhr.send(form);
  });
}

/**
 * Stage a PFP image for processing.
 *
 * @param {File} file
 * @param {(newToken: string, newUsername: string) => void} [onTokenRefreshed]
 * @returns {Promise<{ pfp_upload_id: string, filename: string }>}
 */
export async function uploadPfp(file, onTokenRefreshed) {
  const form = new FormData();
  form.append('file', file);
  const res = await authenticatedFetch('/api/data/upload/pfp', { method: 'POST', body: form }, onTokenRefreshed);
  if (!res.ok) throw new Error('Failed to upload profile picture');
  return res.json();
}

/**
 * Confirm a staged PFP upload and trigger server-side processing.
 *
 * @param {string} pfpUploadId
 * @param {(newToken: string, newUsername: string) => void} [onTokenRefreshed]
 * @returns {Promise<{ pfp_hash: string, pfp_urls: object }>}
 */
export async function confirmPfp(pfpUploadId, onTokenRefreshed) {
  const res = await authenticatedFetch(
    '/api/users/me/pfp',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pfp_upload_id: pfpUploadId }),
    },
    onTokenRefreshed,
  );
  if (!res.ok) throw new Error('Failed to process profile picture');
  return res.json();
}
