import { test, expect } from "@playwright/test";

test("tests page shows AI suggestions panel", async ({ page }) => {
  await page.goto("/tests");
  await expect(page.getByText("AI Suggestions")).toBeVisible();
  // all 4 suggestion titles visible
  await expect(page.getByText("Row count SLA: gig_vendor_stats")).toBeVisible();
  await expect(page.getByText("Null fraction: total_profile_views")).toBeVisible();
  await expect(page.getByText("Value bounds: click_through_rate")).toBeVisible();
  await expect(page.getByText("Freshness SLA: marketing_campaigns")).toBeVisible();
});

test("accepting a suggestion marks it accepted and shows toast", async ({ page }) => {
  await page.goto("/tests");
  // click Accept on first suggestion card
  const firstAccept = page.getByRole("button", { name: /Accept/i }).first();
  await firstAccept.click();
  // toast appears
  await expect(page.getByText("Check added to suite")).toBeVisible();
  // card shows accepted state
  await expect(page.getByText("Added to suite").first()).toBeVisible();
});

test("plain-english authoring generates yaml preview", async ({ page }) => {
  await page.goto("/tests");
  const textarea = page.getByPlaceholder("Describe a check in plain English...");
  await textarea.fill("Check that amount_usd is never negative");
  await page.getByRole("button", { name: /Generate/i }).click();
  // wait for mock 800ms generation
  await page.waitForTimeout(1000);
  await expect(page.getByText("check: custom_check")).toBeVisible();
});
