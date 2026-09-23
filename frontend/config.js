/**
 * Bitget OctaCore - Dynamic Backend & WebSocket Resolver (Developer Configuration)
 * 
 * Connecting the Backend (Developer Options):
 *  1. Vercel Rewrites (Recommended):
 *     In frontend/vercel.json, set the rewrite destination to your deployed backend URL.
 *     Leave getBackendBaseUrl() returning '' so requests use same-origin /api/* and /ws.
 * 
 *  2. Build-time / Global Variable:
 *     Define window.__OCTACORE_BACKEND__ = "https://your-backend.railway.app" before loading.
 * 
 *  3. Testing via URL query parameter:
 *     Append ?backend=https://your-backend.railway.app to test a deployment in the browser.
 */

(function (window) {
  // Check URL query param for rapid developer testing: ?backend=https://...
  const urlParams = new URLSearchParams(window.location.search);
  const paramBackend = urlParams.get('backend') || urlParams.get('api');
  if (paramBackend) {
    try {
      const cleanUrl = paramBackend.replace(/\/+$/, '');
      localStorage.setItem('octacore_backend_url', cleanUrl);
    } catch (e) {}
  }

  function getBackendBaseUrl() {
    // 1. Explicit window override (e.g. injected in CI or script tag)
    if (window.__OCTACORE_BACKEND__) {
      return window.__OCTACORE_BACKEND__.replace(/\/+$/, '');
    }

    // 2. Developer URL override stored from query param
    try {
      const stored = localStorage.getItem('octacore_backend_url');
      if (stored && stored.trim()) {
        return stored.trim().replace(/\/+$/, '');
      }
    } catch (e) {}

    // 3. Default: empty string (relative paths, routed by Vercel rewrites or local server)
    return '';
  }

  function getApiUrl(path) {
    if (!path.startsWith('/')) path = '/' + path;
    const base = getBackendBaseUrl();
    if (base) {
      return `${base}${path}`;
    }
    return path;
  }

  function getWsUrl(path = '/ws') {
    if (!path.startsWith('/')) path = '/' + path;
    const base = getBackendBaseUrl();
    if (base) {
      const wsProto = base.startsWith('https:') ? 'wss:' : 'ws:';
      const cleanHost = base.replace(/^https?:\/\//, '');
      return `${wsProto}//${cleanHost}${path}`;
    }
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.host}${path}`;
  }

  window.OctaCoreConfig = {
    getBackendBaseUrl,
    getApiUrl,
    getWsUrl
  };
})(window);
