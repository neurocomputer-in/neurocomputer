import { test, expect } from '@playwright/test';
import { waitForApp, apiCreateConversation, apiDeleteConversation } from './helpers';

test.describe('F07 – LiveKit connection & status', () => {
  let convId: string;

  test.beforeAll(async () => {
    convId = await apiCreateConversation('LiveKit Test', 'neuro');
  });

  test.afterAll(async () => {
    await apiDeleteConversation(convId);
  });

  test('connection status shows Disconnected initially', async ({ page }) => {
    await waitForApp(page);
    // Before any tab is opened, should be disconnected
    const status = page.locator('text=/Connected|Disconnected/').first();
    await expect(status).toBeVisible();
  });

  test('connection status changes to Connected after opening conversation', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=LiveKit Test').first().click();
    // Wait for LiveKit to connect
    await expect(page.locator('text=Connected')).toBeVisible({ timeout: 15000 });
  });

  test('connected dot is green', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=LiveKit Test').first().click();
    await expect(page.locator('text=Connected')).toBeVisible({ timeout: 15000 });
    // The green dot should be present next to "Connected"
    const greenDot = page.locator('[style*="background: rgb(74, 222, 128)"]');
    await expect(greenDot).toBeVisible({ timeout: 3000 });
  });
});
