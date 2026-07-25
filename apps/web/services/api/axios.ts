import axios from "axios";

// Fall back to the local backend so a missing .env.local doesn't produce a
// literal "undefined" in request URLs.
export const baseApiURL =
  process.env.NEXT_PUBLIC_BASE_API_URL ?? "http://localhost:8000/api/v1";

/**
 * Shared axios instance. Interceptors (Bearer token, 401 handling) are attached
 * once at runtime by hooks/api/useSetupAxios. Request modules override baseURL
 * per domain.
 */
const api = axios.create({
  baseURL: baseApiURL,
});

export default api;
