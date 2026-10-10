import { Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, lazy, Suspense } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Minus, Plus, Trash2 } from "lucide-react";
import { api, errorMessage, money } from "../api/client";
import type { Cart as CartType, User, Restaurant, Order } from "../types";
import { State, Image } from "../components/UI";
const DeliveryMap = lazy(() => import("../components/DeliveryMap"));
const schema = z.object({
  first_name: z.string().trim().min(1, "Введите имя"),
  phone_number: z.string().regex(/^\+?\d{9,15}$/, "Телефон: +996555123456"),
  delivery_address: z.string().trim().min(5, "Укажите полный адрес").max(255),
});
type Fields = z.infer<typeof schema>;
export default function Cart({ checkout = false }: { checkout?: boolean }) {
  const qc = useQueryClient();
  const nav = useNavigate();
  const [message, setMessage] = useState("");
  const [showMap, setShowMap] = useState(false);
  const cart = useQuery({
    queryKey: ["cart"],
    queryFn: async () => (await api.get<CartType>("cart/")).data,
  });
  const me = useQuery({
    queryKey: ["me"],
    queryFn: async () => (await api.get<User>("auth/me/")).data,
  });
  const restaurants = useQuery({
    queryKey: ["cart-restaurants", cart.data?.id, cart.data?.items[0]?.item.id],
    enabled: !!cart.data?.items.length,
    queryFn: async () => {
      const dish = (await api.get(`menu-items/${cart.data!.items[0].item.id}/`))
        .data;
      return (
        await api.get<Restaurant>(`restaurants/${dish.category.restaurant.id}/`)
      ).data;
    },
  });
  const form = useForm<Fields>({
    resolver: zodResolver(schema),
    values: {
      first_name: me.data?.first_name ?? "",
      phone_number: me.data?.phone_number ?? "",
      delivery_address: me.data?.delivery_address ?? "",
    },
  });
  const update = useMutation({
    mutationFn: async ({ id, quantity }: { id?: number; quantity?: number }) =>
      id
        ? quantity
          ? api.patch(`cart/items/${id}/`, { quantity })
          : api.delete(`cart/items/${id}/`)
        : api.post("cart/clear/"),
    onSuccess: (r) => qc.setQueryData(["cart"], r.data),
    onError: (e) => setMessage(errorMessage(e)),
  });
  const place = useMutation({
    mutationFn: async (data: Fields) => {
      await api.patch("auth/me/", data);
      return (
        await api.post<Order>("orders/checkout/", {
          delivery_address: data.delivery_address,
        })
      ).data;
    },
    onSuccess: (order) => {
      qc.invalidateQueries({ queryKey: ["cart"] });
      qc.invalidateQueries({ queryKey: ["orders"] });
      qc.invalidateQueries({ queryKey: ["me"] });
      nav(`/orders/${order.id}`);
    },
    onError: (e) => setMessage(errorMessage(e)),
  });
  const below =
    Number(cart.data?.total_price ?? 0) <
    Number(restaurants.data?.min_order_price ?? 0);
  return (
    <>
      <Link className="back" to="/">
        ← Продолжить выбирать
      </Link>
      <h1>{checkout ? "Почти у вашей двери" : "Ваша корзина"}</h1>
      {message && (
        <div className="notice" role="alert">
          {message}
        </div>
      )}
      <State loading={cart.isPending} error={cart.error}>
        {!cart.data?.items.length ? (
          <div className="empty">
            <span>🧺</span>
            <h2>Здесь будет ваш вкусный заказ</h2>
            <p>Загляните в рестораны и выберите любимые блюда.</p>
            <Link className="button" to="/">
              Выбрать блюда
            </Link>
          </div>
        ) : (
          <div className="checkout-grid">
            <div>
              {cart.data.items.map((ci) => (
                <article className="cart-row panel" key={ci.id}>
                  <Image src={ci.item.photo} alt={ci.item.name} />
                  <div>
                    <h3>{ci.item.name}</h3>
                    <p>
                      {ci.item.weight} г · {money(ci.item.price)}
                    </p>
                    {!ci.item.is_available && (
                      <span className="error">
                        Блюдо недоступно — удалите его
                      </span>
                    )}
                    <div className="quantity">
                      <button
                        aria-label={`Уменьшить ${ci.item.name}`}
                        disabled={update.isPending || ci.quantity <= 1}
                        onClick={() =>
                          update.mutate({
                            id: ci.id,
                            quantity: ci.quantity - 1,
                          })
                        }
                      >
                        <Minus size={16} />
                      </button>
                      <span>{ci.quantity}</span>
                      <button
                        aria-label={`Увеличить ${ci.item.name}`}
                        disabled={update.isPending || ci.quantity >= 99}
                        onClick={() =>
                          update.mutate({
                            id: ci.id,
                            quantity: ci.quantity + 1,
                          })
                        }
                      >
                        <Plus size={16} />
                      </button>
                    </div>
                  </div>
                  <div className="cart-end">
                    <strong>{money(ci.subtotal)}</strong>
                    <button
                      aria-label={`Удалить ${ci.item.name}`}
                      disabled={update.isPending}
                      onClick={() => update.mutate({ id: ci.id })}
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </article>
              ))}
              <button
                disabled={update.isPending}
                onClick={() => update.mutate({})}
              >
                Очистить корзину
              </button>
              {checkout && (
                <form
                  id="checkout-form"
                  className="panel form"
                  onSubmit={form.handleSubmit((data) => place.mutate(data))}
                >
                  <h2>Куда привезти?</h2>
                  {(
                    ["first_name", "phone_number", "delivery_address"] as const
                  ).map((key, i) => (
                    <label key={key}>
                      {["Ваше имя", "Телефон", "Адрес доставки в Бишкеке"][i]}
                      <input
                        autoComplete={
                          ["given-name", "tel", "street-address"][i]
                        }
                        {...form.register(key)}
                      />
                      {form.formState.errors[key] && (
                        <span className="error">
                          {form.formState.errors[key]?.message}
                        </span>
                      )}
                    </label>
                  ))}
                  <div className="address-demo">
                    <strong>Ориентиры в Бишкеке</strong>
                    <p>
                      Можно ввести адрес вручную или открыть бесплатную карту.
                      Она загрузится с OpenStreetMap.
                    </p>
                    <button
                      type="button"
                      onClick={() => setShowMap((value) => !value)}
                    >
                      {showMap ? "Скрыть карту" : "Показать карту OSM"}
                    </button>
                    {showMap && (
                      <Suspense fallback={<p role="status">Загрузка карты…</p>}>
                        <DeliveryMap
                          onSelect={(address) =>
                            form.setValue("delivery_address", address, {
                              shouldValidate: true,
                            })
                          }
                        />
                      </Suspense>
                    )}
                  </div>
                </form>
              )}
            </div>
            <aside className="panel summary">
              <span className="eyebrow">ВАШ ОБЕД</span>
              <h2>{restaurants.data?.name ?? "Заказ"}</h2>
              <div>
                <span>Блюда</span>
                <strong>{money(cart.data.total_price)}</strong>
              </div>
              <div>
                <span>Доставка</span>
                <span>Без доплаты</span>
              </div>
              <hr />
              <div className="total">
                <span>Итого</span>
                <strong>{money(cart.data.total_price)}</strong>
              </div>
              <State loading={restaurants.isPending} error={restaurants.error}>
                <>
                  {below && (
                    <p className="error">
                      Минимальный заказ{" "}
                      {money(restaurants.data?.min_order_price ?? 0)}
                    </p>
                  )}
                  {restaurants.data && !restaurants.data.is_open && (
                    <p className="error">Ресторан сейчас закрыт.</p>
                  )}
                  {checkout ? (
                    <button
                      form="checkout-form"
                      className="button"
                      disabled={
                        place.isPending ||
                        below ||
                        !restaurants.data?.is_open ||
                        cart.data.items.some((i) => !i.item.is_available)
                      }
                    >
                      {place.isPending ? "Оформляем…" : "Подтвердить заказ"}
                    </button>
                  ) : (
                    <button
                      className="button"
                      disabled={
                        below ||
                        !restaurants.data?.is_open ||
                        cart.data.items.some((i) => !i.item.is_available)
                      }
                      onClick={() => nav("/checkout")}
                    >
                      К оформлению →
                    </button>
                  )}
                </>
              </State>
              <p className="muted">
                Никаких банковских операций. Учебная оплата доступна после
                оформления только в деморежиме.
              </p>
            </aside>
          </div>
        )}
      </State>
    </>
  );
}
