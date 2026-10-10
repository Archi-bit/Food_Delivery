import { useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Star, Clock } from "lucide-react";
import { api, money, errorMessage } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { Restaurant as RestaurantType, Page, Review } from "../types";
import { State, Image } from "../components/UI";
export default function Restaurant() {
  const { id } = useParams();
  const auth = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [comment, setComment] = useState("");
  const [stars, setStars] = useState(5);
  const [editing, setEditing] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [reviewPage, setReviewPage] = useState(1);
  const restaurant = useQuery({
    queryKey: ["restaurant", id],
    queryFn: async () =>
      (await api.get<RestaurantType>(`restaurants/${id}/`)).data,
  });
  const reviews = useQuery({
    queryKey: ["reviews", id, reviewPage],
    queryFn: async () =>
      (
        await api.get<Page<Review>>("reviews/", {
          params: { restaurant: id, page: reviewPage },
        })
      ).data,
  });
  const me = useQuery({
    queryKey: ["me"],
    enabled: auth,
    queryFn: async () => (await api.get<{ username: string }>("auth/me/")).data,
  });
  const add = useMutation({
    mutationFn: (item: number) =>
      api.post("cart/items/", { item, quantity: 1 }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cart"] });
      setMessage("Добавлено в корзину");
    },
    onError: (e) => setMessage(errorMessage(e)),
  });
  const review = useMutation({
    mutationFn: async () => {
      if (editing) {
        await api.patch(`reviews/${editing}/`, { stars, comment });
      } else {
        await api.post("reviews/", { restaurant: Number(id), stars, comment });
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reviews"] });
      qc.invalidateQueries({ queryKey: ["restaurant"] });
      setComment("");
      setEditing(null);
      setMessage("Отзыв сохранён");
    },
    onError: (e) => setMessage(errorMessage(e)),
  });
  const remove = useMutation({
    mutationFn: (reviewId: number) => api.delete(`reviews/${reviewId}/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reviews"] });
      qc.invalidateQueries({ queryKey: ["restaurant"] });
    },
    onError: (e) => setMessage(errorMessage(e)),
  });
  return (
    <State loading={restaurant.isPending} error={restaurant.error}>
      {restaurant.data && (
        <>
          <Link className="back" to="/">
            ← Все рестораны
          </Link>
          <section className="restaurant-hero">
            <Image src={restaurant.data.logo} alt={restaurant.data.name} />
            <div>
              <span className="eyebrow">ВКУСЫ БИШКЕКА</span>
              <h1>{restaurant.data.name}</h1>
              <p>{restaurant.data.description}</p>
              <div className="meta">
                <span>
                  <Star size={17} /> {restaurant.data.avg_rating} ·{" "}
                  {restaurant.data.reviews_count} отзывов
                </span>
                <span>
                  <Clock size={17} /> {restaurant.data.delivery_time} мин
                </span>
                <span>От {money(restaurant.data.min_order_price)}</span>
              </div>
              <p className="muted">{restaurant.data.address}</p>
              {!restaurant.data.is_open && (
                <div className="notice">
                  Ресторан закрыт. Оформление заказа недоступно.
                </div>
              )}
            </div>
          </section>
          <nav className="menu-nav" aria-label="Меню">
            {restaurant.data.categories?.map((c) => (
              <a key={c.id} href={`#category-${c.id}`}>
                {c.name}
              </a>
            ))}
          </nav>
          {message && (
            <div className="notice" role="status">
              {message} <Link to="/cart">Открыть корзину</Link>
            </div>
          )}
          {restaurant.data.categories?.map((c) => (
            <section id={`category-${c.id}`} key={c.id}>
              <h2>{c.name}</h2>
              <div className="dish-grid">
                {c.items.map((d) => (
                  <article className="dish-card" key={d.id}>
                    <Image src={d.photo} alt={d.name} />
                    <div className="card-body">
                      <h3>{d.name}</h3>
                      <p>{d.weight} г</p>
                      <div className="card-bottom">
                        <strong>{money(d.price)}</strong>
                        <button
                          className="add"
                          aria-label={`Добавить ${d.name}`}
                          disabled={
                            !d.is_available ||
                            !restaurant.data?.is_open ||
                            add.isPending
                          }
                          onClick={() =>
                            auth ? add.mutate(d.id) : navigate("/login")
                          }
                        >
                          <Plus size={20} />
                        </button>
                      </div>
                      {!d.is_available && (
                        <span className="muted">Сегодня закончилось</span>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ))}
          <section>
            <h2>Отзывы гостей</h2>
            <State loading={reviews.isPending} error={reviews.error}>
              <div className="reviews">
                {reviews.data?.results.map((r) => (
                  <article key={r.id} className="panel">
                    <strong>
                      {r.user} · {"★".repeat(r.stars)}
                    </strong>
                    <p>{r.comment}</p>
                    {me.data?.username === r.user && (
                      <div className="actions">
                        <button
                          onClick={() => {
                            setEditing(r.id);
                            setStars(r.stars);
                            setComment(r.comment);
                          }}
                        >
                          Изменить
                        </button>
                        <button
                          disabled={remove.isPending}
                          onClick={() => remove.mutate(r.id)}
                        >
                          Удалить
                        </button>
                      </div>
                    )}
                  </article>
                ))}
              </div>
              {!reviews.data?.count && (
                <p>Станьте первым гостем, оставившим отзыв.</p>
              )}
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
            {auth ? (
              <form
                className="panel form"
                onSubmit={(e) => {
                  e.preventDefault();
                  review.mutate();
                }}
              >
                <h3>{editing ? "Изменить отзыв" : "Ваш отзыв"}</h3>
                <label>
                  Оценка
                  <select
                    value={stars}
                    onChange={(e) => setStars(Number(e.target.value))}
                  >
                    {[5, 4, 3, 2, 1].map((s) => (
                      <option key={s} value={s}>
                        {s} ★
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Впечатления
                  <textarea
                    maxLength={2000}
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                  />
                </label>
                <button className="button" disabled={review.isPending}>
                  Сохранить отзыв
                </button>
                {editing && (
                  <button
                    type="button"
                    onClick={() => {
                      setEditing(null);
                      setComment("");
                    }}
                  >
                    Отмена
                  </button>
                )}
              </form>
            ) : (
              <Link to="/login">Войдите, чтобы оставить отзыв</Link>
            )}
          </section>
        </>
      )}
    </State>
  );
}
