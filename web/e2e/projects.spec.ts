import { expect, test } from "@playwright/test";

test("opens with the server token and lists indexed projects", async ({ page }) => {
  const securityPolicyViolations: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      securityPolicyViolations.push(message.text());
    }
  });

  await page.goto("/#token=e2e-token");

  await expect(page.getByText(/seeded-project/)).toBeVisible();
  await expect(page.getByText("Indexed")).toBeVisible();
  expect(new URL(page.url()).hash).toBe("");
  expect(securityPolicyViolations).toEqual([]);
});

test("asks for a new link without the token", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Open Delphi Code from your terminal" })).toBeVisible();
});
