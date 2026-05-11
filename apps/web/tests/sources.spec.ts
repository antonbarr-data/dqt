import { test, expect } from "@playwright/test";

test("Add Connection opens wizard", async ({ page }) => {
  await page.goto("/sources");
  await page.getByRole("link", { name: /Add Connection/i }).first().click();
  await expect(page.locator("h1")).toContainText("Add Connection");
  await expect(page.getByText("Configure")).toBeVisible();
});

test("wizard Test Connection shows health checklist", async ({ page }) => {
  await page.goto("/sources/new/bigquery");
  // click Test Connection
  await page.getByRole("button", { name: /Test Connection/i }).click();
  // step 2 shows health check items
  await expect(page.getByText("TCP Reach")).toBeVisible();
  await expect(page.getByText("Authentication")).toBeVisible();
  await expect(page.getByText("Info Schema Read")).toBeVisible();
});

test("wizard reaches step 3 after health check completes", async ({ page }) => {
  await page.goto("/sources/new/bigquery");
  await page.getByRole("button", { name: /Test Connection/i }).click();
  // wait for all 6 health steps to animate (6 * 320ms + buffer)
  await page.waitForTimeout(2500);
  await expect(page.getByRole("button", { name: /Configure Tables/i })).toBeEnabled();
  await page.getByRole("button", { name: /Configure Tables/i }).click();
  await expect(page.getByText("marketing_campaigns")).toBeVisible();
});
