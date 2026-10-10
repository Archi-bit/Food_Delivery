import axios from "axios";
let access = "";
let sessionVersion = 0;
let refreshing: Promise<string> | null = null;
let restoring: Promise<void> | null = null;
export function setTokens(tokens?: { access: string }) {
  sessionVersion += 1;
  access = tokens?.access ?? "";
  refreshing = null;
  window.dispatchEvent(new Event("auth-change"));
}
export const authenticated = () => Boolean(access);
const options = {
  baseURL: "/api/",
  timeout: 15000,
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
};
export const browserAuth = axios.create(options);
export const api = axios.create(options);
export function restoreSession(): Promise<void> {
  if (!restoring) {
    const version = sessionVersion;
    const request = browserAuth
      .get("auth/csrf/")
      .then(() => browserAuth.get("auth/session/"))
      .then((r) => {
        if (version === sessionVersion)
          setTokens(r.data.access ? { access: r.data.access } : undefined);
      })
      .finally(() => {
        if (restoring === request) restoring = null;
      });
    restoring = request;
  }
  return restoring;
}
export async function logoutSession() {
  await browserAuth.post("auth/session/logout/");
  setTokens();
}
api.interceptors.request.use((config) => {
  if (access) config.headers.Authorization = `Bearer ${access}`;
  else delete config.headers.Authorization;
  return config;
});
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const config = error.config;
    if (error.response?.status !== 401 || !access || !config || config._retry)
      throw error;
    config._retry = true;
    const version = sessionVersion;
    try {
      if (!refreshing) {
        const request = browserAuth
          .get("auth/session/")
          .then((r) => {
            if (version !== sessionVersion) throw new Error("Сессия завершена");
            if (!r.data.access)
              throw new Error("Сессия истекла. Войдите снова.");
            access = r.data.access;
            return access;
          })
          .finally(() => {
            if (refreshing === request) refreshing = null;
          });
        refreshing = request;
      }
      await refreshing;
      if (version !== sessionVersion) throw new Error("Сессия завершена");
      return await api(config);
    } catch (e) {
      if (version === sessionVersion) setTokens();
      throw e;
    }
  },
);
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    if (data && typeof data === "object")
      return Object.values(data)
        .flat()
        .map((v) => (typeof v === "string" ? v : JSON.stringify(v)))
        .join(" ");
    return "Не удалось связаться с сервером. Попробуйте ещё раз.";
  }
  return error instanceof Error ? error.message : "Произошла ошибка";
}
export const money = (value: string | number) =>
  `${Number(value).toLocaleString("ru-RU")} сом`;
