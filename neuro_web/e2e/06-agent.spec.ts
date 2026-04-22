import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers';

test.describe('F06 – Agent selection', () => {
  test('agent dropdown shows current agent name', async ({ page }) => {
    await waitForApp(page);
    // TopBar has agent dropdown with "Neuro" by default
    await expect(page.locator('text=Neuro').first()).toBeVisible();
  });

  test('clicking agent dropdown opens agent list', async ({ page }) => {
    await waitForApp(page);
    // Click the dropdown trigger (has "▾")
    await page.locator('text=▾').first().click();
    // Dropdown renders items with descriptions — check descriptions are unique
    await expect(page.locator('text=Web automation & scraping')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('text=Code assistant')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('text=Upwork automation')).toBeVisible({ timeout: 3000 });
  });

  test('agent list shows descriptions', async ({ page }) => {
    await waitForApp(page);
    await page.locator('text=▾').first().click();
    await expect(page.locator('text=Web automation & scraping')).toBeVisible({ timeout: 3000 });
  });

  test('selecting OpenClaw updates dropdown label', async ({ page }) => {
    await waitForApp(page);
    await page.locator('text=▾').first().click();
    await page.locator('text=OpenClaw').first().click();
    await expect(page.locator('text=OpenClaw').first()).toBeVisible({ timeout: 3000 });
    // ▾ should still be present (dropdown closed)
    await expect(page.locator('text=▾')).toBeVisible();
  });

  test('clicking outside closes dropdown', async ({ page }) => {
    await waitForApp(page);
    await page.locator('text=▾').first().click();
    await expect(page.locator('text=Web automation & scraping')).toBeVisible();
    await page.locator('body').click({ position: { x: 600, y: 400 } });
    await expect(page.locator('text=Web automation & scraping')).not.toBeVisible({ timeout: 3000 });
  });

  test('selected agent shows checkmark in dropdown', async ({ page }) => {
    await waitForApp(page);
    await page.locator('text=▾').first().click();
    // Default Neuro should have ✓
    await expect(page.locator('text=✓')).toBeVisible({ timeout: 3000 });
  });
});
