import { test, expect } from "@playwright/test";

test("overview page loads", async ({ page }) => {
  await page.goto("/overview");
  await expect(page).not.toHaveTitle(/Error/);
  await expect(page.locator("h1")).toContainText("Overview");
});

test("datasets page loads", async ({ page }) => {
  await page.goto("/datasets");
  await expect(page.locator("h1")).toContainText("Datasets");
  // table rows visible
  await expect(page.getByRole("cell", { name: "marketing_campaigns" })).toBeVisible();
});

test("sources page loads", async ({ page }) => {
  await page.goto("/sources");
  await expect(page.locator("h1")).toContainText("Sources");
  await expect(page.getByText("Add Connection")).toBeVisible();
});

test("tests page loads", async ({ page }) => {
  await page.goto("/tests");
  await expect(page.getByText("AI Suggestions")).toBeVisible();
});
