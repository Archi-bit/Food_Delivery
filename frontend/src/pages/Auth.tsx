import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { browserAuth, setTokens, errorMessage } from "../api/client";
import { useQueryClient } from "@tanstack/react-query";
const schema = z.object({
  username: z.string().min(1, "Введите имя пользователя"),
  password: z.string().min(1, "Введите пароль"),
  email: z.string(),
  password2: z.string(),
});
type Fields = z.infer<typeof schema>;
export default function Auth({ register = false }: { register?: boolean }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [error, setError] = useState("");
  const form = useForm<Fields>({
    resolver: zodResolver(schema),
    defaultValues: { username: "", password: "", email: "", password2: "" },
  });
  const submit = form.handleSubmit(async (data) => {
    setError("");
    if (
      register &&
      (data.password.length < 8 ||
        data.password !== data.password2 ||
        !z.email().safeParse(data.email).success)
    ) {
      setError(
        "Введите корректный email и совпадающие пароли длиной от 8 символов.",
      );
      return;
    }
    try {
      const r = await browserAuth.post(
        register ? "auth/session/register/" : "auth/session/login/",
        register ? data : { username: data.username, password: data.password },
      );
      setTokens({ access: r.data.access });
      qc.clear();
      nav("/profile");
    } catch (e) {
      setError(errorMessage(e));
    }
  });
  return (
    <div className="auth-layout">
      <div className="auth-story">
        <span className="eyebrow">ВАШ СТОЛИК ВСЕГДА ГОТОВ</span>
        <h1>
          Рады видеть
          <br />
          вас за столом.
        </h1>
        <p>
          Сохраняйте адрес, выбирайте любимые блюда
          <br />и следите за заказами в одном месте.
        </p>
        <span className="auth-emoji">🍊</span>
      </div>
      <form className="panel form" onSubmit={submit}>
        <h2>{register ? "Создать аккаунт" : "Добро пожаловать"}</h2>
        <p className="muted">
          {register
            ? "Всего минута — и можно выбирать обед."
            : "Войдите, чтобы заказать что-нибудь вкусное."}
        </p>
        <label>
          Имя пользователя
          <input autoComplete="username" {...form.register("username")} />
        </label>
        {register && (
          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              {...form.register("email")}
            />
          </label>
        )}
        <label>
          Пароль
          <input
            type="password"
            autoComplete={register ? "new-password" : "current-password"}
            {...form.register("password")}
          />
        </label>
        {register && (
          <label>
            Повторите пароль
            <input
              type="password"
              autoComplete="new-password"
              {...form.register("password2")}
            />
          </label>
        )}
        {Object.values(form.formState.errors).map((e, i) => (
          <p role="alert" key={i}>
            {e.message}
          </p>
        ))}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button className="button" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting
            ? "Подождите…"
            : register
              ? "Зарегистрироваться"
              : "Войти"}
        </button>
        <Link to={register ? "/login" : "/register"}>
          {register
            ? "Уже есть аккаунт? Войти"
            : "Нет аккаунта? Зарегистрироваться"}
        </Link>
        <small className="muted">
          Вход сохраняется на 7 дней. Выйти можно в личном кабинете.
        </small>
      </form>
    </div>
  );
}
