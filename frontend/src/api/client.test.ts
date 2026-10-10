// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
import axios, { type InternalAxiosRequestConfig } from "axios";
import {
  api,
  browserAuth,
  setTokens,
  authenticated,
  errorMessage,
  restoreSession,
  logoutSession,
} from "./client";
const originalAdapter = api.defaults.adapter;
const originalSessionAdapter = browserAuth.defaults.adapter;
afterEach(() => {
  api.defaults.adapter = originalAdapter;
  browserAuth.defaults.adapter = originalSessionAdapter;
  setTokens();
  vi.restoreAllMocks();
});
function expired(config: InternalAxiosRequestConfig): never {
  throw new axios.AxiosError("expired", "401", config, undefined, {
    status: 401,
    statusText: "Unauthorized",
    headers: {},
    config,
    data: {},
  });
}
describe("Сессия и JWT", () => {
  it("не сохраняет токены в браузерном хранилище", () => {
    setTokens({ access: "access" });
    expect(authenticated()).toBe(true);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    setTokens();
    expect(authenticated()).toBe(false);
  });
  it("отправляет Bearer API серверу", async () => {
    setTokens({ access: "test-token" });
    api.defaults.adapter = async (config) => {
      expect(config.headers.Authorization).toBe("Bearer test-token");
      return {
        data: { ok: true },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      };
    };
    expect((await api.get("cart/")).data.ok).toBe(true);
  });
  it("восстанавливает вход из HttpOnly сессии", async () => {
    const paths: string[] = [];
    browserAuth.defaults.adapter = async (config) => {
      paths.push(config.url!);
      return {
        data:
          config.url === "auth/csrf/"
            ? { csrf_token: "csrf" }
            : { access: "restored", user: { username: "guest" } },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      };
    };
    await restoreSession();
    expect(paths).toEqual(["auth/csrf/", "auth/session/"]);
    expect(authenticated()).toBe(true);
  });
  it("анонимная сессия не авторизует", async () => {
    browserAuth.defaults.adapter = async (config) => ({
      data: { access: null, user: null },
      status: 200,
      statusText: "OK",
      headers: {},
      config,
    });
    await restoreSession();
    expect(authenticated()).toBe(false);
  });
  it("обновляет access при 401 один раз", async () => {
    setTokens({ access: "old" });
    const refresh = vi
      .spyOn(browserAuth, "get")
      .mockResolvedValue({ data: { access: "new" } });
    let calls = 0;
    api.defaults.adapter = async (config) => {
      calls++;
      if (config.headers.Authorization !== "Bearer new") expired(config);
      return {
        data: { ok: true },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      };
    };
    await api.get("auth/me/");
    expect(calls).toBe(2);
    expect(refresh).toHaveBeenCalledExactlyOnceWith("auth/session/");
  });
  it("параллельные 401 используют одно восстановление", async () => {
    setTokens({ access: "old" });
    const refresh = vi
      .spyOn(browserAuth, "get")
      .mockResolvedValue({ data: { access: "new" } });
    api.defaults.adapter = async (config) => {
      if (config.headers.Authorization !== "Bearer new") expired(config);
      return { data: {}, status: 200, statusText: "OK", headers: {}, config };
    };
    await Promise.all([api.get("cart/"), api.get("auth/me/")]);
    expect(refresh).toHaveBeenCalledTimes(1);
  });
  it("истекшая сессия завершает вход", async () => {
    setTokens({ access: "old" });
    vi.spyOn(browserAuth, "get").mockResolvedValue({ data: { access: null } });
    api.defaults.adapter = async (config) => expired(config);
    await expect(api.get("cart/")).rejects.toThrow("Сессия истекла");
    expect(authenticated()).toBe(false);
  });
  it("повторные 401 не вызывают цикл", async () => {
    setTokens({ access: "old" });
    const refresh = vi
      .spyOn(browserAuth, "get")
      .mockResolvedValue({ data: { access: "new" } });
    let requests = 0;
    api.defaults.adapter = async (config) => {
      requests++;
      expired(config);
    };
    await expect(api.get("cart/")).rejects.toThrow();
    expect(requests).toBe(2);
    expect(refresh).toHaveBeenCalledTimes(1);
  });
  it("выход отзывает серверную сессию", async () => {
    setTokens({ access: "old" });
    const logout = vi
      .spyOn(browserAuth, "post")
      .mockResolvedValue({ status: 204 });
    await logoutSession();
    expect(logout).toHaveBeenCalledExactlyOnceWith("auth/session/logout/");
    expect(authenticated()).toBe(false);
  });
  it("поздний refresh не восстанавливает завершённую сессию", async () => {
    setTokens({ access: "old" });
    let resolveRefresh: (value: unknown) => void = () => {};
    vi.spyOn(browserAuth, "get").mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRefresh = resolve;
        }),
    );
    api.defaults.adapter = async (config) => expired(config);
    const request = api.get("cart/");
    await vi.waitFor(() => expect(browserAuth.get).toHaveBeenCalled());
    setTokens();
    resolveRefresh({ data: { access: "late" } });
    await expect(request).rejects.toThrow("Сессия завершена");
    expect(authenticated()).toBe(false);
  });
  it("использует CSRF cookie и header", () => {
    expect(browserAuth.defaults.xsrfCookieName).toBe("csrftoken");
    expect(browserAuth.defaults.xsrfHeaderName).toBe("X-CSRFToken");
    expect(browserAuth.defaults.withCredentials).toBe(true);
  });
  it("сообщения понятны пользователю", () =>
    expect(errorMessage(new Error("Пустая корзина"))).toBe("Пустая корзина"));
});
