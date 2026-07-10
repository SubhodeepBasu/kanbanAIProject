import { expect, test, type Page } from "@playwright/test";

const seedBoard = {
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
    { id: "col-discovery", title: "Discovery", cardIds: ["card-3"] },
    {
      id: "col-progress",
      title: "In Progress",
      cardIds: ["card-4", "card-5"],
    },
    { id: "col-review", title: "Review", cardIds: ["card-6"] },
    { id: "col-done", title: "Done", cardIds: ["card-7", "card-8"] },
  ],
  cards: {
    "card-1": {
      id: "card-1",
      title: "Align roadmap themes",
      details: "Draft quarterly themes with impact statements and metrics.",
    },
    "card-2": {
      id: "card-2",
      title: "Gather customer signals",
      details: "Review support tags, sales notes, and churn feedback.",
    },
    "card-3": {
      id: "card-3",
      title: "Prototype analytics view",
      details: "Sketch initial dashboard layout and key drill-downs.",
    },
    "card-4": {
      id: "card-4",
      title: "Refine status language",
      details: "Standardize column labels and tone across the board.",
    },
    "card-5": {
      id: "card-5",
      title: "Design card layout",
      details: "Add hierarchy and spacing for scanning dense lists.",
    },
    "card-6": {
      id: "card-6",
      title: "QA micro-interactions",
      details: "Verify hover, focus, and loading states.",
    },
    "card-7": {
      id: "card-7",
      title: "Ship marketing page",
      details: "Final copy approved and asset pack delivered.",
    },
    "card-8": {
      id: "card-8",
      title: "Close onboarding sprint",
      details: "Document release notes and share internally.",
    },
  },
};

const signIn = async (page: Page) => {
  await page.getByPlaceholder("user").fill("user");
  await page.getByPlaceholder("password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
};

test.beforeEach(async ({ request }) => {
  const response = await request.put("/api/board?username=user", {
    data: { board: seedBoard },
  });
  expect(response.ok()).toBeTruthy();
});

test("rejects invalid login", async ({ page }) => {
  await page.goto("/");
  await page.getByPlaceholder("user").fill("bad");
  await page.getByPlaceholder("password").fill("credentials");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByText("Invalid credentials. Use user / password.")).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(0);
});

test("loads the kanban board", async ({ page }) => {
  await page.goto("/");
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await page.goto("/");
  await signIn(page);
  const uniqueTitle = `Playwright card ${Date.now()}`;
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(uniqueTitle);
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText(uniqueTitle)).toBeVisible();
  await page.reload();
  await expect(page.getByText(uniqueTitle)).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await page.goto("/");
  await signIn(page);

  const sourceColumn = page.getByTestId("column-col-backlog");
  const card = sourceColumn.locator('[data-testid^="card-"]').first();
  const cardTestId = await card.getAttribute("data-testid");
  if (!cardTestId) {
    throw new Error("Unable to resolve source card test id.");
  }

  await card.scrollIntoViewIfNeeded();
  const targetColumn = page.getByTestId("column-col-discovery");
  const targetCard = targetColumn.locator('[data-testid^="card-"]').first();
  await targetCard.scrollIntoViewIfNeeded();

  const cardBox = await card.boundingBox();
  const targetCardBox = await targetCard.boundingBox();
  if (!cardBox || !targetCardBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    targetCardBox.x + targetCardBox.width / 2,
    targetCardBox.y + targetCardBox.height / 2,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByTestId(cardTestId)).toBeVisible();
});
