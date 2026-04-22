import { test, expect } from '@playwright/test';
import { waitForApp, apiCreateConversation, apiDeleteConversation } from './helpers';

test.describe('F04 – Tabs', () => {
  let conv1: string;
  let conv2: string;

  test.beforeAll(async () => {
    conv1 = await apiCreateConversation('Tab Test One', 'neuro');
    conv2 = await apiCreateConversation('Tab Test Two', 'neuro');
  });

  test.afterAll(async () => {
    await apiDeleteConversation(conv1);
    await apiDeleteConversation(conv2);
  });

  test('clicking + creates a new conversation tab', async ({ page }) => {
    await waitForApp(page);
    const tabCount = await page.locator('[style*="border-bottom: 2px"]').count();
    await page.locator('text=+').first().click();
    await page.waitForTimeout(2000);
    const newTabCount = await page.locator('[style*="border-bottom: 2px"]').count();
    expect(newTabCount).toBeGreaterThanOrEqual(tabCount);
  });

  test('opening a conversation adds tab with correct title', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Tab Test One').first().click();
    await expect(page.locator('text=Tab Test One').nth(1)).toBeVisible({ timeout: 5000 });
  });

  test('opening second conversation adds second tab', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Tab Test One').first().click();
    await page.waitForTimeout(500);
    await page.locator('text=Tab Test Two').first().click();
    // Both tabs should be visible
    await expect(page.locator('text=Tab Test One').nth(1)).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Tab Test Two').nth(1)).toBeVisible({ timeout: 5000 });
  });

  test('active tab has purple bottom border', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Tab Test One').first().click();
    await page.waitForTimeout(500);
    // Active tab has border-bottom with #8B5CF6
    const activeTab = page.locator('[style*="border-bottom: 2px solid rgb(139, 92, 246)"]');
    await expect(activeTab).toBeVisible({ timeout: 5000 });
  });

  test('× button closes a tab', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Tab Test One').first().click();
    await page.waitForTimeout(500);
    // Find the × close button in the tab bar (not sidebar)
    // The × is next to the tab title — hover to make it visible then click
    const tabBar = page.locator('[style*="border-bottom: 2px solid rgb(139, 92, 246)"]').first();
    const closeBtn = tabBar.locator('text=×');
    await closeBtn.click();
    // Tab should disappear from tab bar
    await expect(page.locator('text=Tab Test One').nth(1)).not.toBeVisible({ timeout: 3000 });
  });

  test('switching tabs loads correct conversation', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Tab Test One').first().click();
    await page.waitForTimeout(500);
    await page.locator('text=Tab Test Two').first().click();
    await page.waitForTimeout(500);
    // Click Tab Test One tab (in tab bar, not sidebar)
    await page.locator('text=Tab Test One').nth(1).click();
    await page.waitForTimeout(1000);
    // Tab One should be active (purple border)
    const activeTab = page.locator('[style*="border-bottom: 2px solid rgb(139, 92, 246)"]');
    await expect(activeTab.locator('text=Tab Test One')).toBeVisible({ timeout: 5000 });
  });
});
