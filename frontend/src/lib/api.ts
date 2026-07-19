import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

const API_URL = import.meta.env.VITE_API_URL || "/api/v1";

export function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp("(?:^|; )" + name.replace(/([.$?*|{}()\[\]\\\/\+^])/g, "\\$1") + "=([^;]*)"));
  return m ? decodeURIComponent(m[1]) : null;
}

export function getCsrfToken(): string | null {
  return getCookie("supmeal_csrf");
}

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true, // envoie les cookies httpOnly
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  // En dev (Swagger / tests), on garde le Bearer via localStorage en fallback
  const token = localStorage.getItem("supmeal_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // CSRF double-submit : sur les requetes mutantes, on envoie le cookie supmeal_csrf en header
  const method = (config.method || "get").toLowerCase();
  if (["post", "put", "patch", "delete"].includes(method)) {
    const csrf = getCookie("supmeal_csrf");
    if (csrf && config.headers) {
      (config.headers as Record<string, string>)["X-CSRF-Token"] = csrf;
    }
  }

  // Important pour les uploads: laisser le navigateur/axios poser
  // automatiquement le multipart/form-data avec le bon boundary.
  if (typeof FormData !== "undefined" && config.data instanceof FormData && config.headers) {
    delete (config.headers as Record<string, string>)["Content-Type"];
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Purge local + redirection
      localStorage.removeItem("supmeal_token");
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
