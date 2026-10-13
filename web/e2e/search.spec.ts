import { expect, test } from "@playwright/test";
import { consoleErrorsOf } from "./consoleErrors";

test("finds code in a picked project and highlights it", async ({ page }) => {
  const consoleErrors = consoleErrorsOf(page);
  await page.goto("/#token=e2e-token");

  await page.getByRole("textbox", { name: "What are you looking for?" }).fill("where are passwords checked");
  await page.getByRole("combobox", { name: "Project" }).click();
  await page.getByRole("option", { name: /seeded-project/ }).click();
  await page.getByRole("button", { name: "Search" }).click();

  const result = page.getByRole("article").filter({ hasText: "auth.py" });
  await expect(result).toBeVisible();
  await expect(result.locator('[style*="--shiki-light"]').first()).toBeVisible();
  const address = new URL(page.url());
  expect(address.searchParams.get("q")).toBe("where are passwords checked");
  expect(address.searchParams.get("project")).toMatch(/seeded-project/);

  await page.reload();
  await expect(page.getByRole("article").filter({ hasText: "auth.py" })).toBeVisible();
  expect(consoleErrors).toEqual([]);
});

test("long lines scroll inside their snippet instead of widening the page", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/?q=passwords#token=e2e-token");

  await expect(page.getByRole("article").filter({ hasText: "auth.py" })).toBeVisible();
  const widths = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, window: innerWidth }));
  expect(widths.page).toBe(widths.window);
});
