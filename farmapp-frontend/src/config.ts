/**
 * Runtime configuration.
 *
 * The API base URL is resolved at runtime so one image can be deployed to
 * every environment:
 *   1. window.__APP_CONFIG__.apiBaseUrl — written to /config.js by the nginx
 *      container on startup from the API_BASE_URL env var (Helm: apiBaseUrl)
 *   2. VITE_API_BASE_URL — build-time override (e.g. local .env)
 *   3. "/api" — same-origin; the ingress (and the Vite dev proxy) routes
 *      /api/* to the backend service
 */

declare global {
  interface Window {
    __APP_CONFIG__?: {
      apiBaseUrl?: string;
    };
  }
}

export const apiBaseUrl: string =
  window.__APP_CONFIG__?.apiBaseUrl ||
  import.meta.env.VITE_API_BASE_URL ||
  "/api";
