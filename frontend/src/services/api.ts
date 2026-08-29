import axios, { type AxiosError, type AxiosInstance } from 'axios';

// Vite bakes VITE_API_URL in at *build* time, not container runtime. Local
// dev (docker-compose.dev.yml / frontend/.env.example) sets it explicitly to
// an absolute http://localhost:8000/api/v1. In a production build there is
// no VITE_API_URL in the build context, so it falls back to a relative path
// -- correct because nginx.conf proxies /api to the backend on the same
// origin, whatever public domain/IP that ends up being.
const baseURL: string = (import.meta.env.VITE_API_URL as string | undefined) ?? '/api/v1';

const api: AxiosInstance = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface ApiErrorResponse {
  detail?: string;
  message?: string;
}

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorResponse>) => {
    const message =
      error.response?.data?.detail ??
      error.response?.data?.message ??
      error.message ??
      'An unexpected error occurred';

    return Promise.reject(new Error(message));
  }
);

export default api;
