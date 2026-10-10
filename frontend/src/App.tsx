import { Routes, Route, Link, Navigate, useNavigate } from "react-router-dom";
import { MapPin, ShoppingBag, UserRound, Utensils, Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import type { Cart as CartType } from "./types";
import { api } from "./api/client";
import { useAuth } from "./hooks/useAuth";
import Catalog from "./pages/Catalog";
import Restaurant from "./pages/Restaurant";
import Auth from "./pages/Auth";
import Cart from "./pages/Cart";
import Profile from "./pages/Profile";
import Order from "./pages/Order";
function Protected({ children }: { children: ReactNode }) {
  return useAuth() ? children : <Navigate to="/login" replace />;
}
export default function App() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [headerSearch, setHeaderSearch] = useState("");
  const cart = useQuery({
    queryKey: ["cart"],
    enabled: auth,
    queryFn: async () => (await api.get<CartType>("cart/")).data,
  });
  const count =
    cart.data?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0;
  return (
    <>
      <a href="#main" className="skip-link">
        К содержимому
      </a>
      <header>
        <div className="header-inner">
          <Link className="logo" to="/">
            <span>
              <Utensils size={21} />
            </span>
            тамак<span className="logo-dot">.</span>
          </Link>
          <div className="location">
            <MapPin size={18} />
            <div>
              <small>Доставляем в</small>
              <strong>Бишкек</strong>
            </div>
          </div>
          <form
            className="header-search"
            role="search"
            onSubmit={(event) => {
              event.preventDefault();
              navigate(
                `/?search=${encodeURIComponent(headerSearch)}#restaurants`,
              );
            }}
          >
            <input
              aria-label="Поиск из шапки"
              placeholder="Найти любимую кухню"
              value={headerSearch}
              onChange={(event) => setHeaderSearch(event.target.value)}
            />
            <button aria-label="Найти ресторан">
              <Search size={18} />
            </button>
          </form>
          <nav aria-label="Главная навигация">
            <Link className="catalog-link" to="/">
              Рестораны и блюда
            </Link>
            <Link className="icon-link" to={auth ? "/profile" : "/login"}>
              <UserRound size={20} />
              <span>{auth ? "Профиль" : "Войти"}</span>
            </Link>
            <Link className="cart-link" to="/cart">
              <ShoppingBag size={19} />
              <span>Корзина</span>
              <b>{auth ? count : 0}</b>
            </Link>
          </nav>
        </div>
      </header>
      <main id="main">
        <Routes>
          <Route path="/" element={<Catalog />} />
          <Route path="/restaurants" element={<Catalog />} />
          <Route path="/restaurants/:id" element={<Restaurant />} />
          <Route path="/login" element={<Auth />} />
          <Route path="/register" element={<Auth register />} />
          <Route
            path="/cart"
            element={
              <Protected>
                <Cart />
              </Protected>
            }
          />
          <Route
            path="/checkout"
            element={
              <Protected>
                <Cart checkout />
              </Protected>
            }
          />
          <Route
            path="/profile"
            element={
              <Protected>
                <Profile />
              </Protected>
            }
          />
          <Route
            path="/orders/:id"
            element={
              <Protected>
                <Order />
              </Protected>
            }
          />
          <Route
            path="*"
            element={
              <div className="empty">
                <h1>Страница не найдена</h1>
                <Link to="/">На главную</Link>
              </div>
            }
          />
        </Routes>
      </main>
      <footer>
        <div>
          <Link className="logo" to="/">
            тамак.
          </Link>
          <p>Вкусный повод остаться дома.</p>
        </div>
        <div>
          <strong>Сделано для Бишкека</strong>
          <p>
            Учебный проект · рестораны вымышлены
            <br />
            Никаких реальных платежей и доставки.
          </p>
        </div>
        <div>
          <a href="/api/schema/swagger-ui/">Документация API</a>
          <p>React + Django · {new Date().getFullYear()}</p>
        </div>
      </footer>
    </>
  );
}
