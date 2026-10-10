import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowUpRight, Clock, Star, SlidersHorizontal } from "lucide-react";
import { api, money } from "../api/client";
import type { Page, Restaurant, Dish } from "../types";
import { State, Image } from "../components/UI";
const categories = [
  ["🍽️", "Все", ""],
  ["🍕", "Пицца", "pizza"],
  ["🍜", "Лагман", "lagman"],
  ["🥟", "Манты", "manty"],
  ["🥗", "Салат", "salad"],
  ["🍰", "Десерты", "desserts"],
];
export default function Catalog() {
  const [params, setParams] = useSearchParams();
  const search = params.get("search") ?? "";
  const updateParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
    setPage(1);
  };
  const category =
    categories.find((entry) => entry[2] === params.get("food_category"))?.[2] ??
    "";
  const categoryName = categories.find((entry) => entry[2] === category)![1];
  const [open, setOpen] = useState(false);
  const [sort, setSort] = useState("-avg_rating");
  const [page, setPage] = useState(1);
  const restaurants = useQuery({
    queryKey: ["restaurants", search, open, sort, page, category],
    queryFn: async () =>
      (
        await api.get<Page<Restaurant>>("restaurants/", {
          params: {
            search,
            is_open: open || undefined,
            ordering: sort,
            page,
            food_category: category || undefined,
          },
        })
      ).data,
  });
  const dishes = useQuery({
    queryKey: ["dishes", category],
    queryFn: async () =>
      (
        await api.get<
          Page<
            Dish & { category: { restaurant: { id: number; name: string } } }
          >
        >("menu-items/", {
          params: {
            is_available: true,
            food_category: category || undefined,
          },
        })
      ).data,
  });
  const dishSection = (
    <section>
      <div className="section-top">
        <div>
          <span className="eyebrow">ЧТО-НИБУДЬ ВКУСНОЕ</span>
          <h2>{category ? categoryName : "Вдохновение для обеда"}</h2>
        </div>
      </div>
      <State loading={dishes.isPending} error={dishes.error}>
        <div className="dish-grid">
          {dishes.data?.results.slice(0, 8).map((d) => (
            <Link
              key={d.id}
              className="dish-card"
              to={`/restaurants/${d.category.restaurant.id}`}
            >
              <Image src={d.photo} alt={d.name} />
              <div className="card-body">
                <h3>{d.name}</h3>
                <p>
                  {d.category.restaurant.name} · {d.weight} г
                </p>
                <strong>{money(d.price)}</strong>
              </div>
            </Link>
          ))}
        </div>
        {!dishes.data?.count && (
          <div className="empty">Блюда этой категории пока не найдены.</div>
        )}
      </State>
    </section>
  );
  return (
    <>
      <section className="hero">
        <div>
          <span className="eyebrow">С ЛЮБОВЬЮ К БИШКЕКУ</span>
          <h1>
            Хороший день
            <br />
            начинается с <em>еды.</em>
          </h1>
          <p>
            Любимые кухни города — у вашей двери.
            <br />
            Выбирайте вкусное, а остальное оставьте нам.
          </p>
          <a href="#restaurants" className="button">
            Выбрать ресторан <ArrowUpRight size={18} />
          </a>
          <span className="hero-note">
            Учебный сервис · без реальных платежей
          </span>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orbit" />
          <div className="plate">
            <span>🥗</span>
          </div>
          <div className="floating label-one">Свежо. Вкусно. По-домашнему.</div>
          <div className="floating label-two">🌿 Маленькая пауза для себя</div>
        </div>
      </section>
      <div className="category-row" aria-label="Категории блюд">
        {categories.map(([icon, name, slug]) => (
          <button
            key={name}
            className={category === slug ? "category active" : "category"}
            aria-pressed={category === slug}
            onClick={() => updateParam("food_category", slug)}
          >
            <span>{icon}</span>
            {name}
          </button>
        ))}
      </div>
      {category && dishSection}
      <section id="restaurants">
        <div className="section-top">
          <div>
            <span className="eyebrow">ВАШИ НОВЫЕ ЛЮБИМЫЕ МЕСТА</span>
            <h2>
              {category
                ? `Рестораны · ${categoryName.toLowerCase()}`
                : "Рестораны рядом"}{" "}
              <span className="count">{restaurants.data?.count ?? "…"}</span>
            </h2>
          </div>
          <span className="muted">Бишкек · цены в сомах</span>
        </div>
        <div className="filters">
          <label className="search">
            <SlidersHorizontal size={18} />
            <input
              aria-label="Поиск ресторанов"
              placeholder="Название или кухня"
              value={search}
              onChange={(e) => {
                updateParam("search", e.target.value);
                setPage(1);
              }}
            />
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={open}
              onChange={(e) => {
                setOpen(e.target.checked);
                setPage(1);
              }}
            />{" "}
            Сейчас открыты
          </label>
          <select
            aria-label="Сортировка"
            value={sort}
            onChange={(e) => {
              setSort(e.target.value);
              setPage(1);
            }}
          >
            <option value="-avg_rating">Сначала лучшие</option>
            <option value="delivery_time">Быстрее доставят</option>
            <option value="min_order_price">Минимальный заказ</option>
            <option value="name">По названию</option>
          </select>
        </div>
        <State loading={restaurants.isPending} error={restaurants.error}>
          <div className="restaurant-grid">
            {restaurants.data?.results.map((r) => (
              <Link
                className="restaurant-card"
                key={r.id}
                to={`/restaurants/${r.id}`}
              >
                <div className="cover">
                  <Image src={r.logo} alt={r.name} />
                  <span className="delivery">
                    <Clock size={14} /> {r.delivery_time}–{r.delivery_time + 10}{" "}
                    мин
                  </span>
                  {!r.is_open && <span className="closed">Закрыт</span>}
                </div>
                <div className="card-body">
                  <div className="card-title">
                    <h3>{r.name}</h3>
                    <span className="rating">
                      <Star size={14} fill="currentColor" />
                      {r.avg_rating.toFixed(1)}
                    </span>
                  </div>
                  <p>{r.description}</p>
                  <div className="card-bottom">
                    <span>Заказ от {money(r.min_order_price)}</span>
                    <ArrowUpRight size={18} />
                  </div>
                </div>
              </Link>
            ))}
          </div>
          {restaurants.data?.count === 0 && (
            <div className="empty">
              Здесь пока тихо. Попробуйте другой запрос.
            </div>
          )}
          <div className="pagination">
            <button disabled={page === 1} onClick={() => setPage(page - 1)}>
              Назад
            </button>
            <span>Страница {page}</span>
            <button
              disabled={!restaurants.data?.next}
              onClick={() => setPage(page + 1)}
            >
              Далее
            </button>
          </div>
        </State>
      </section>
      {!category && dishSection}
      <section className="manifesto">
        <span>🌿</span>
        <div>
          <h2>Большой город. Маленькие радости.</h2>
          <p>
            Знакомые вкусы, новые открытия и время для того, что вам нравится.
          </p>
        </div>
      </section>
    </>
  );
}
