import { test, expect } from "@playwright/test";
test("Регистрация → меню → корзина → заказ → демооплата → история → отзыв", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const username = `journey_${info.project.name}_${Date.now()}`;
  await page.goto("/register");
  await page.getByLabel("Имя пользователя").fill(username);
  await page
    .getByLabel("Email", { exact: true })
    .fill(`${username}@example.invalid`);
  await page.getByLabel("Пароль", { exact: true }).fill("PortfolioJourney923!");
  await page.getByLabel("Повторите пароль").fill("PortfolioJourney923!");
  await page.getByRole("button", { name: "Зарегистрироваться" }).click();
  await expect(
    page.getByRole("heading", { name: `Привет, ${username}!` }),
  ).toBeVisible();
  const sessionCookie = (await page.context().cookies()).find(
    (cookie) => cookie.name === "sessionid",
  );
  expect(sessionCookie?.httpOnly).toBe(true);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: `Привет, ${username}!` }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Выйти", exact: true }).click();
  await page.reload();

  await expect(page).toHaveURL(/login/);
  await page.getByLabel("Имя пользователя").fill(username);
  await page.getByLabel("Пароль", { exact: true }).fill("PortfolioJourney923!");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: `Привет, ${username}!` }),
  ).toBeVisible();
  await page.getByRole("link", { name: "тамак.", exact: true }).first().click();
  await page.getByLabel("Поиск ресторанов").fill("Тёплый двор");
  await page.locator(".restaurant-card").first().click();
  await expect(
    page.getByRole("heading", { name: "Тёплый двор", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Добавить Плов с говядиной", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Добавлено");
  await page.getByRole("link", { name: "Открыть корзину" }).click();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Ваша корзина", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Плов с говядиной", exact: true }),
  ).toBeVisible();

  await page.getByRole("button", { name: "К оформлению →" }).click();
  await page.getByLabel("Ваше имя").fill("Учебный гость");
  await page.getByLabel("Телефон").fill("+996555123456");
  // Simulate unavailable tiles locally: no automated requests reach OSM.
  await page.route("https://tile.openstreetmap.org/**", (route) =>
    route.abort(),
  );
  await page.getByRole("button", { name: "Показать карту OSM" }).click();
  await expect(
    page.getByText(
      "Карта недоступна. Можно выбрать учебный адрес ниже или ввести свой.",
    ),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: "Демо: Бишкек, проспект Чуй, 100",
      exact: true,
    })
    .click();
  await expect(page.getByLabel("Адрес доставки в Бишкеке")).toHaveValue(
    "Демо: Бишкек, проспект Чуй, 100",
  );

  await page
    .getByLabel("Адрес доставки в Бишкеке")
    .fill("Бишкек, демо-улица, дом 12");
  await page.getByRole("button", { name: "Подтвердить заказ" }).click();
  await expect(page.getByRole("heading", { name: /Заказ #/ })).toBeVisible();
  await page
    .getByRole("button", { name: "Оплатить · демо", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Деньги не списывались");
  await page.getByRole("button", { name: "Следующий статус" }).click();
  await expect(page.locator(".timeline .done")).toHaveCount(2);
  await page.getByRole("link", { name: "← История заказов" }).click();
  await expect(page.locator(".order-card").first()).toContainText(
    "Тёплый двор",
  );
  await page.getByRole("link", { name: "тамак.", exact: true }).first().click();
  await page.getByLabel("Поиск ресторанов").fill("Тёплый двор");
  await page.locator(".restaurant-card").first().click();
  await page.getByLabel("Впечатления").fill("Учебный отзыв: вкусно и удобно.");
  await page.getByRole("button", { name: "Сохранить отзыв" }).click();
  await expect(page.getByRole("status")).toContainText("Отзыв сохранён");
  await page
    .locator("img")
    .evaluateAll((images) => images.forEach((img) => (img.loading = "eager")));
  await page.waitForFunction(() =>
    Array.from(document.images).every((img) => img.complete),
  );
  await page.screenshot({
    path: `test-results/restaurant-${info.project.name}.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});
test("Каталог: фильтры, пагинация, пустое состояние и мобильная сетка", async ({
  page,
}, info) => {
  await page.goto("/");
  await expect(page.locator(".restaurant-card")).toHaveCount(10);
  await page
    .locator("img")
    .evaluateAll((images) => images.forEach((img) => (img.loading = "eager")));
  await page.waitForFunction(() =>
    Array.from(document.images).every((img) => img.complete),
  );
  await page.screenshot({
    path: `test-results/catalog-${info.project.name}.png`,
    fullPage: true,
  });
  await page.getByLabel("Сортировка").selectOption("delivery_time");
  await expect(page.locator(".restaurant-card").first()).toContainText(
    "20–30 мин",
  );
  await page.getByRole("button", { name: "Далее", exact: true }).click();
  await expect(page.getByText("Страница 2")).toBeVisible();
  await page.getByLabel("Поиск ресторанов").fill("Несуществующий ресторан 999");
  await expect(
    page.getByText("Здесь пока тихо. Попробуйте другой запрос."),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("Категории еды фильтруют реальный каталог и сохраняются после обновления", async ({
  page,
}) => {
  await page.goto("/?search=E2E");
  await expect(page.locator(".restaurant-card")).toHaveCount(2);
  await page.getByRole("button", { name: "🍕 Пицца", exact: true }).click();
  await expect(page.locator(".restaurant-card")).toHaveCount(1);
  await expect(page.locator(".restaurant-card")).toContainText(
    "E2E кухня: пицца",
  );
  await expect(page).toHaveURL(/food_category=pizza/);
  await page.reload();
  await expect(page.locator(".restaurant-card")).toHaveCount(1);
  await expect(
    page.getByRole("button", { name: "🍕 Пицца", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "🍜 Лагман", exact: true }).click();
  await expect(page.locator(".restaurant-card")).toHaveCount(1);
  await expect(page.locator(".restaurant-card")).toContainText(
    "E2E кухня: лагман",
  );
  await page.getByRole("button", { name: "🍽️ Все", exact: true }).click();
  await expect(page.locator(".restaurant-card")).toHaveCount(2);
  await page.getByLabel("Поиск ресторанов").fill("");
  await page.getByRole("button", { name: "Далее", exact: true }).click();
  await expect(page.getByText("Страница 2")).toBeVisible();
  for (const [label, slug] of [
    ["🍕 Пицца", "pizza"],
    ["🍜 Лагман", "lagman"],
    ["🥟 Манты", "manty"],
    ["🥗 Салат", "salad"],
    ["🍰 Десерты", "desserts"],
  ]) {
    await page.getByRole("button", { name: label, exact: true }).click();
    await expect(page.getByText("Страница 1")).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`food_category=${slug}`));
    await expect(page.locator(".dish-card").first()).toBeVisible();
    if (slug !== "desserts") {
      await expect(page.locator(".dish-card h3").first()).toContainText(
        new RegExp(
          slug === "pizza" ? "пицца|маргарита" : label.split(" ")[1],
          "i",
        ),
      );
    }
  }
  await expect(
    page.locator(".dish-card").filter({ hasText: "Ягодный чизкейк" }).first(),
  ).toBeVisible();
});

test("Поиск ресторана не зависит от регистра кириллицы", async ({ page }) => {
  await page.goto("/");
  for (const search of [
    "базилик и тесто",
    "БАЗИЛИК И ТЕСТО",
    "бАзИлИк И тЕсТо",
    "Базилик и тесто",
  ]) {
    const response = page.waitForResponse((r) => {
      const url = new URL(r.url());
      return (
        url.pathname === "/api/restaurants/" &&
        url.searchParams.get("search") === search
      );
    });
    await page.getByLabel("Поиск ресторанов").fill(search);
    expect((await response).status()).toBe(200);
    await expect(page.locator(".restaurant-card")).toHaveCount(1);
    await expect(page.locator(".restaurant-card")).toContainText(
      "Базилик и тесто",
    );
  }
  await page.getByRole("button", { name: "🍕 Пицца", exact: true }).click();
  await expect(page.locator(".restaurant-card")).toHaveCount(1);
  await page.reload();
  await expect(page.getByLabel("Поиск ресторанов")).toHaveValue(
    "Базилик и тесто",
  );
  await expect(page.locator(".restaurant-card")).toHaveCount(1);
});
