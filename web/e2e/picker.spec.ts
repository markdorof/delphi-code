import { expect, test } from "@playwright/test";
import { consoleErrorsOf } from "./consoleErrors";

test("tracks and then stops tracking a repository picked from an account", async ({ page }) => {
  const consoleErrors = consoleErrorsOf(page);
  const activity = page.getByRole("region", { name: "Activity" });
  const pickedRow = page.getByRole("row").filter({ hasText: "bitbucket.org/acme/api" });
  await page.goto("/projects#token=e2e-token");

  await page.getByRole("link", { name: "From your account" }).click();
  await page.getByRole("option", { name: /Acme/ }).click();
  await page.getByRole("checkbox", { name: /^api/ }).click();
  await page.getByRole("checkbox", { name: "Index them now" }).click();
  await page.getByRole("button", { name: "Apply changes" }).click();

  await expect(page).toHaveURL(/\/projects$/);
  await expect(activity.getByText("Now tracking 1 project; run Sync all to index it.")).toBeVisible();
  await expect(pickedRow).toContainText("Tracked");

  await page.getByRole("link", { name: "From your account" }).click();
  await page.getByRole("option", { name: /Acme/ }).click();
  const api = page.getByRole("checkbox", { name: /^api/ });
  await expect(api).toBeChecked();
  await api.click();
  await expect(page.getByText("Stop tracking and delete the index of")).toBeVisible();
  await page.getByRole("button", { name: "Apply changes" }).click();

  await expect(activity.getByText("Stopped tracking 1 repository.")).toBeVisible();
  await expect(pickedRow).toHaveCount(0);
  expect(consoleErrors).toEqual([]);
});
