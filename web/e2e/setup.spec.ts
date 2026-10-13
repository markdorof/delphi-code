import { expect, test } from "@playwright/test";
import { consoleErrorsOf } from "./consoleErrors";

test("checks the installation on the real server", async ({ page }) => {
  const consoleErrors = consoleErrorsOf(page);
  await page.goto("/setup#token=e2e-token");

  await page.getByRole("button", { name: "Run checks" }).click();

  const checks = page.getByRole("definition");
  await expect(checks.filter({ hasText: /^2 dimensions, self-distance/ })).toBeVisible();
  await expect(checks.filter({ hasText: "yes (python_audit)" })).toBeVisible();
  expect(consoleErrors).toEqual([]);
});

test("explains why importing a model failed", async ({ page }) => {
  await page.goto("/setup#token=e2e-token");

  await page.getByLabel(/import a prepared model folder/).fill("/no/such/model/folder");
  await page.getByRole("button", { name: "Import" }).click();

  const activity = page.getByRole("region", { name: "Activity" });
  await expect(activity.getByRole("alert")).toContainText("Missing or linked model asset");
  await expect(activity.getByRole("link", { name: "Set up the model" })).toHaveCount(0);
  await expect(activity.getByRole("heading", { name: "Importing the model from /no/such/model/folder" })).toBeVisible();
});
