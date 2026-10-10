import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Check, Package, ChefHat, Bike } from "lucide-react";
import { api, money, errorMessage } from "../api/client";
import type { Order as OrderType } from "../types";
import { State } from "../components/UI";
export default function Order() {
  const { id } = useParams();
  const qc = useQueryClient();
  const [message, setMessage] = useState("");
  const order = useQuery({
    queryKey: ["order", id],
    queryFn: async () => (await api.get<OrderType>(`orders/${id}/`)).data,
    refetchInterval: 15000,
  });
  const health = useQuery({
    queryKey: ["health"],
    queryFn: async () =>
      (await api.get<{ demo_mode: boolean }>("health/")).data,
  });
  const action = useMutation({
    mutationFn: async ({
      payment,
      success,
    }: {
      payment: boolean;
      success?: boolean;
    }) =>
      (
        await api.post(
          `orders/${id}/${payment ? "demo-payment" : "demo-advance"}/`,
          payment ? { success } : {},
        )
      ).data,
    onSuccess: (data) => {
      setMessage(
        data.demo
          ? data.success
            ? "Демонстрационная оплата успешна. Деньги не списывались."
            : "Демонстрационная оплата отклонена. Можно повторить."
          : "Демонстрационный статус обновлён",
      );
      qc.invalidateQueries({ queryKey: ["order", id] });
      qc.invalidateQueries({ queryKey: ["orders"] });
    },
    onError: (e) => setMessage(errorMessage(e)),
  });
  const steps = [
    ["new", "Принят", Package],
    ["preparing", "Готовится", ChefHat],
    ["on_way", "У курьера", Bike],
    ["delivered", "Доставлен", Check],
  ] as const;
  return (
    <State loading={order.isPending} error={order.error}>
      {order.data && (
        <>
          <Link className="back" to="/profile">
            ← История заказов
          </Link>
          <span className="eyebrow">ВКУСНОЕ УЖЕ БЛИЗКО</span>
          <h1>Заказ #{order.data.id}</h1>
          <p>
            {order.data.restaurant.name} · {order.data.delivery_address}
          </p>
          <div className="timeline">
            {steps.map(([value, label, Icon], i) => (
              <div
                key={value}
                className={
                  i <= steps.findIndex((s) => s[0] === order.data?.status)
                    ? "done"
                    : ""
                }
              >
                <Icon />
                <strong>{label}</strong>
              </div>
            ))}
          </div>
          <div className="panel">
            <h2>Ваш заказ</h2>
            {order.data.order_items.map((item) => (
              <div className="line-item" key={item.id}>
                <span>
                  {item.item.name} × {item.quantity}
                </span>
                <strong>{money(item.subtotal)}</strong>
              </div>
            ))}
            <hr />
            <div className="line-item">
              <strong>Итого</strong>
              <strong>{money(order.data.total_price)}</strong>
            </div>
          </div>
          {health.data?.demo_mode && (
            <section className="panel demo-panel">
              <span className="eyebrow">УЧЕБНАЯ СИМУЛЯЦИЯ</span>
              <h2>Оплата и доставка в деморежиме</h2>
              <div className="address-demo" role="note">
                <strong>Демо-SMS внутри приложения</strong>
                <p>
                  Заказ #{order.data.id}: {order.data.status_display}. Это
                  имитация сообщения, реальное SMS не отправлялось.
                </p>
              </div>
              <p>
                Кнопки управляют имитацией. Банковские данные не нужны, деньги
                не списываются. Статус продвигается вручную.
              </p>
              <div className="actions">
                <button
                  className="button"
                  disabled={action.isPending}
                  onClick={() =>
                    action.mutate({ payment: true, success: true })
                  }
                >
                  Оплатить · демо
                </button>
                <button
                  disabled={action.isPending}
                  onClick={() =>
                    action.mutate({ payment: true, success: false })
                  }
                >
                  Имитировать отказ
                </button>
                <button
                  disabled={
                    action.isPending || order.data?.status === "delivered"
                  }
                  onClick={() => action.mutate({ payment: false })}
                >
                  Следующий статус
                </button>
              </div>
              {message && <p role="status">{message}</p>}
            </section>
          )}
        </>
      )}
    </State>
  );
}
