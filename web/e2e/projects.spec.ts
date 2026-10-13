import { expect, test } from "@playwright/test";
import { consoleErrorsOf } from "./consoleErrors";

test("opens with the server token and lists indexed projects", async ({ page }) => {
  const consoleErrors = consoleErrorsOf(page);

  await page.goto("/projects#token=e2e-token");

  await expect(page.getByText(/seeded-project/)).toBeVisible();
  await expect(page.getByText("Indexed")).toBeVisible();
  expect(new URL(page.url()).hash).toBe("");
  expect(consoleErrors).toEqual([]);
});

test("asks for a new link without the token", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Open Delphi Code from your terminal" })).toBeVisible();
});
