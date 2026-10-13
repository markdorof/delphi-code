import { expect, test } from "@playwright/test";
import { consoleErrorsOf } from "./consoleErrors";
import { ADDABLE_PROJECT } from "./fixturePaths";

test("opens with the server token and lists indexed projects", async ({ page }) => {
  const consoleErrors = consoleErrorsOf(page);

  await page.goto("/projects#token=e2e-token");

  await expect(page.getByText(/seeded-project/)).toBeVisible();
  expect(new URL(page.url()).hash).toBe("");
  expect(consoleErrors).toEqual([]);
});

test("asks for a new link without the token and takes one pasted into the same tab", async ({ page }) => {
  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "Open Delphi Code from your terminal" })).toBeVisible();

  await page.goto("/projects#token=e2e-token");

  await expect(page.getByText(/seeded-project/)).toBeVisible();
});

test("re-indexes, adds, syncs and removes projects with streamed progress", async ({ page }) => {
  const consoleErrors = consoleErrorsOf(page);
  const activity = page.getByRole("region", { name: "Activity" });
  await page.goto("/projects#token=e2e-token");

  await page.getByRole("button", { name: /^Re-index .*seeded-project/ }).click();
  await expect(activity.getByText(/^Indexed 1 file into \d+ chunks?\.$/)).toBeVisible();

  await page.getByRole("button", { name: "Add projects" }).click();
  await page.getByLabel("Folders or repositories, one per line").fill(ADDABLE_PROJECT);
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(activity.getByText("1 project indexed.")).toBeVisible();
  const addedRow = page.getByRole("row").filter({ hasText: "delphi-code-e2e-addable-project" });
  await expect(addedRow).toContainText("Tracked");

  await page.getByRole("button", { name: "Sync all" }).click();
  await expect(activity.getByRole("heading", { name: "Syncing tracked projects" })).toBeVisible();
  await expect(activity.getByText("1 project indexed.")).toBeVisible();

  await addedRow.getByRole("button", { name: /^Remove / }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Remove" }).click();
  await expect(page.getByRole("status")).toContainText("and deleted its index.");
  await expect(addedRow).toHaveCount(0);
  expect(consoleErrors).toEqual([]);
});
