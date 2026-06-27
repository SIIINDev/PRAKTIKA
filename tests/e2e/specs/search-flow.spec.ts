import { test, expect } from "@playwright/test";
import path from "node:path";

const FIXTURES = path.resolve(__dirname, "../../fixtures");
const DOCX = path.join(FIXTURES, "lecture_databases.docx");

test.describe("Knowledge-base critical path", () => {
  test("upload a DOCX, index it, search and see highlighted results, then empty state", async ({
    page,
  }) => {
    // 1. Open the app.
    await page.goto("/");

    // 2. Go to Документы.
    await page.getByTestId("nav-documents").click();
    await expect(page.getByTestId("dropzone")).toBeVisible();

    // 3. Upload lecture_databases.docx via the hidden file input.
    await page.getByTestId("file-input").setInputFiles(DOCX);

    // 4. Wait until a doc-list-item for this file reaches status "Готово".
    const docItem = page
      .getByTestId("doc-list-item")
      .filter({ hasText: "lecture_databases.docx" })
      .first();
    await expect(docItem).toBeVisible({ timeout: 30_000 });
    await expect(docItem.locator('[data-status="done"]')).toContainText("Готово", {
      timeout: 30_000,
    });

    // 5. Switch to Поиск.
    await page.getByTestId("nav-search").click();
    await expect(page.getByTestId("search-input")).toBeVisible();

    // 6. Search a known query.
    await page.getByTestId("search-input").fill("база данных");
    await page.getByTestId("search-button").click();

    // 7. Assert >= 1 result card with file name + score + a <mark> highlight.
    const cards = page.getByTestId("result-card");
    await expect(cards.first()).toBeVisible({ timeout: 15_000 });
    expect(await cards.count()).toBeGreaterThanOrEqual(1);

    const first = cards.first();
    await expect(first.locator(".result-file")).not.toBeEmpty();
    // Score is rendered with .toFixed(2) so it looks like e.g. "1.99".
    await expect(first.locator(".result-score")).toHaveText(/\d+\.\d{2}/);
    await expect(first.locator("mark").first()).toBeVisible();

    // 8. Search gibberish -> empty state.
    await page.getByTestId("search-input").fill("zzzнетакого");
    await page.getByTestId("search-button").click();

    const empty = page.getByTestId("empty-state");
    await expect(empty).toBeVisible({ timeout: 15_000 });
    await expect(empty).toContainText("ничего не найдено");
    await expect(page.getByTestId("result-card")).toHaveCount(0);
  });
});
