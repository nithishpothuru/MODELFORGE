/**
 * Centralized API Client for ModelForge
 * Connects to FastAPI backend at VITE_API_BASE_URL (defaults to http://127.0.0.1:8000)
 */

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '');

export const API_V1_PREFIX = `${API_BASE_URL}/api/v1`;

/**
 * Get stored authentication token if present
 */
function getAuthToken() {
  try {
    const sessionStr = localStorage.getItem('modelforge_auth_session');
    if (sessionStr) {
      const session = JSON.parse(sessionStr);
      return session?.access_token || session?.token || null;
    }
  } catch (err) {
    console.warn('Failed to parse auth session from localStorage', err);
  }
  return null;
}

/**
 * General JSON fetch request helper
 */
export async function apiRequest(endpoint, options = {}) {
  const url = endpoint.startsWith('http')
    ? endpoint
    : `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const token = getAuthToken();
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (networkError) {
    const isConnRefused =
      networkError.name === 'TypeError' ||
      (networkError.message && networkError.message.toLowerCase().includes('fetch'));

    const msg = isConnRefused
      ? `Cannot reach ModelForge API at ${url}. Ensure the FastAPI server is running: python -m uvicorn app.main:app --port 8000`
      : networkError.message || 'Network error occurred while connecting to ModelForge API.';

    const err = new Error(msg);
    err.isNetworkError = true;
    err.originalError = networkError;
    throw err;
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  let data;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    data = await response.json().catch(() => null);
  } else {
    data = await response.text().catch(() => null);
  }

  if (!response.ok) {
    const errorMessage =
      (typeof data === 'object' && data?.detail) ||
      (typeof data === 'string' && data) ||
      `HTTP Error ${response.status}: ${response.statusText}`;
    const error = new Error(errorMessage);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

/**
 * Multipart/Form-Data File Upload helper with upload progress callback
 */
export async function apiUpload(endpoint, formData, onProgress = null) {
  const url = endpoint.startsWith('http')
    ? endpoint
    : `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url, true);

    const token = getAuthToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percentComplete = Math.round((event.loaded / event.total) * 100);
          onProgress(percentComplete);
        }
      };
    }

    xhr.onload = () => {
      let responseData;
      try {
        responseData = JSON.parse(xhr.responseText);
      } catch {
        responseData = xhr.responseText;
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(responseData);
      } else {
        const errorDetail =
          (typeof responseData === 'object' && responseData?.detail) ||
          `Upload failed with status ${xhr.status}`;
        const error = new Error(errorDetail);
        error.status = xhr.status;
        error.data = responseData;
        reject(error);
      }
    };

    xhr.onerror = () => {
      reject(
        new Error(
          `Network error during file upload to ${url}. Ensure the FastAPI backend is running.`
        )
      );
    };

    xhr.send(formData);
  });
}

/**
 * System Health Endpoints
 */
export async function checkBackendHealth() {
  return apiRequest('/health');
}

export async function checkSupabaseHealth() {
  return apiRequest('/health/supabase');
}

export async function getRootInfo() {
  return apiRequest('/');
}

export default {
  API_BASE_URL,
  API_V1_PREFIX,
  apiRequest,
  apiUpload,
  checkBackendHealth,
  checkSupabaseHealth,
  getRootInfo,
};
