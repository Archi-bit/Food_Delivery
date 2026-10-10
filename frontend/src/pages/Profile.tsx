import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useState } from "react";
import { api, money, errorMessage, logoutSession } from "../api/client";
import type { User, Order, Page, Review } from "../types";
import { State } from "../components/UI";
export default function Profile() {
  const qc = useQueryClient();
  const logout = useMutation({
    mutationFn: logoutSession,
    onSuccess: () => qc.clear(),
    onError: (e) => setMessage(errorMessage(e)),
  });
  const [message, setMessage] = useState("");
  const [page, setPage] = useState(1);
  const me = useQuery({
    queryKey: ["me"],
    queryFn: async () => (await api.get<User>("auth/me/")).data,
  });
  const orders = useQuery({
    queryKey: ["orders", page],
    queryFn: async () =>
      (await api.get<Page<Order>>("orders/", { params: { page } })).data,
  });
  const form = useForm<
    Pick<
      User,
      "first_name" | "last_name" | "email" | "phone_number" | "delivery_address"
    >
  >({ values: me.data });
  const save = useMutation({
    mutationFn: (
      data: Pick<
        User,
        | "first_name"
        | "last_name"
        | "email"
        | "phone_number"
        | "delivery_address"
      >,
    ) => api.patch("auth/me/", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me"] });
      setMessage("Профиль сохранён");
    },
    onError: (e) => setMessage(errorMessage(e)),
  });
  const [reviewPage, setReviewPage] = useState(1);
  const reviews = useQuery({
    queryKey: ["profile-reviews", me.data?.username, reviewPage],
    enabled: !!me.data,
    queryFn: async () =>
      (
        await api.get<Page<Review>>("reviews/", {
          params: { user: me.data!.id, page: reviewPage },
        })
      ).data,
  });
  return (
    <>
      <div className="section-top">
        <div>
          <span className="eyebrow">ВАШ ЛИЧНЫЙ УГОЛОК</span>
          <h1>
            Привет, {me.data?.first_name || me.data?.username || "гость"}!
          </h1>
        </div>
        <button disabled={logout.isPending} onClick={() => logout.mutate()}>
          Выйти
        </button>
      </div>
      <div className="profile-grid">
        <State loading={me.isPending} error={me.error}>
          <form
            className="panel form"
            onSubmit={form.handleSubmit((d) => save.mutate(d))}
          >
            <h2>Профиль и адрес</h2>
            {(
              [
                "first_name",
                "last_name",
                "email",
                "phone_number",
                "delivery_address",
              ] as const
            ).map((key, i) => (
              <label key={key}>
                {["Имя", "Фамилия", "Email", "Телефон", "Адрес доставки"][i]}
                <input
                  type={key === "email" ? "email" : "text"}
                  {...form.register(key)}
                />
              </label>
            ))}
            {message && <p role="status">{message}</p>}
            <button className="button" disabled={save.isPending}>
              Сохранить
            </button>
          </form>
        </State>
        <section>
          <h2>История заказов</h2>
          <State loading={orders.isPending} error={orders.error}>
            {orders.data?.results.map((o) => (
              <Link
                className="order-card panel"
                to={`/orders/${o.id}`}
                key={o.id}
              >
                <div>
                  <strong>
                    #{o.id} · {o.restaurant.name}
                  </strong>
                  <span className="badge">{o.status_display}</span>
                </div>
                <p>
                  {new Date(o.created_date).toLocaleString("ru-RU")} ·{" "}
                  {o.delivery_address}
                </p>
                <strong>{money(o.total_price)}</strong>
              </Link>
            ))}
            {orders.data?.count === 0 && (
              <div className="empty">
                Первый заказ ещё впереди.{" "}
                <Link to="/">Посмотреть рестораны</Link>
              </div>
            )}
            <div className="pagination">
              <button disabled={page === 1} onClick={() => setPage(page - 1)}>
                Назад
              </button>
              <span>{page}</span>
              <button
                disabled={!orders.data?.next}
                onClick={() => setPage(page + 1)}
              >
                Далее
              </button>
            </div>
          </State>
        </section>
      </div>
      <section>
        <h2>Мои отзывы</h2>
        <State loading={reviews.isPending} error={reviews.error}>
          <div className="reviews">
            {reviews.data?.results.map((r) => (
              <article className="panel" key={r.id}>
                <strong>{"★".repeat(r.stars)}</strong>
                <p>{r.comment}</p>
                <Link to={`/restaurants/${r.restaurant}`}>
                  Открыть ресторан и изменить отзыв →
                </Link>
              </article>
            ))}
          </div>
          {reviews.data?.count === 0 && <p>Вы пока не оставили отзывов.</p>}
          <div className="pagination">
            <button
              disabled={reviewPage === 1}
              onClick={() => setReviewPage(reviewPage - 1)}
            >
              Назад
            </button>
            <span>{reviewPage}</span>
            <button
              disabled={!reviews.data?.next}
              onClick={() => setReviewPage(reviewPage + 1)}
            >
              Далее
            </button>
          </div>
        </State>
      </section>
    </>
  );
}
