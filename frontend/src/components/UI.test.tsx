// @vitest-environment jsdom
import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { State, Image } from "./UI";
import { money } from "../api/client";
afterEach(cleanup);
describe("Состояния интерфейса", () => {
  it("показывает доступную загрузку", () => {
    render(
      <State loading>
        <p>Секрет</p>
      </State>,
    );
    expect(screen.getByLabelText("Загрузка")).toBeInTheDocument();
    expect(screen.queryByText("Секрет")).toBeNull();
  });
  it("отображает ошибку и повтор", () => {
    render(<State error={new Error("Сервер недоступен")}>Данные</State>);
    expect(screen.getByRole("alert")).toHaveTextContent("Сервер недоступен");
    expect(
      screen.getByRole("button", { name: "Повторить" }),
    ).toBeInTheDocument();
  });
  it("показывает данные после загрузки", () => {
    render(
      <State>
        <p>Рестораны Бишкека</p>
      </State>,
    );
    expect(screen.getByText("Рестораны Бишкека")).toBeInTheDocument();
  });
  it("изображение имеет альтернативный текст", () => {
    render(<Image src="/media/food.jpg" alt="Манты" />);
    expect(screen.getByRole("img", { name: "Манты" })).toHaveAttribute(
      "src",
      "/media/food.jpg",
    );
  });
  it("нет фото — есть доступная иллюстрация", () => {
    render(<Image src={null} alt="Плов" />);
    expect(screen.getByRole("img", { name: "Плов" })).toBeInTheDocument();
  });
  it("использует сом", () => expect(money("450.00")).toBe("450 сом"));
});
