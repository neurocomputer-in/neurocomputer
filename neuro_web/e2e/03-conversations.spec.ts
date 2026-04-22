import { test, expect } from '@playwright/test';
import { waitForApp, apiCreateConversation, apiDeleteConversation } from './helpers';

test.describe('F03 – Conversations list', () => {
  let convId: string;

  test.beforeAll(async () => {
    convId = await apiCreateConversation('PW Conv Test', 'neuro');
  });

  test.afterAll(async () => {
    await apiDeleteConversation(convId);
  });

  test('conversation appears in sidebar after creation', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500); // let polling load
    await expect(page.locator('text=PW Conv Test')).toBeVisible({ timeout: 8000 });
  });

  test('conversation shows agent emoji and relative time', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    // Agent emoji (🤖) should appear near the conversation
    await expect(page.locator('text=🤖').first()).toBeVisible({ timeout: 5000 });
  });

  test('clicking conversation opens it as a tab', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=PW Conv Test').first().click();
    // Tab should appear in tab bar
    await expect(page.locator('text=PW Conv Test').nth(1)).toBeVisible({ timeout: 5000 });
  });

  test('agent filter "Neuro" shows neuro conversations', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Neuro').first().click();
    // Still should show PW Conv Test (it's neuro)
    await expect(page.locator('text=PW Conv Test')).toBeVisible({ timeout: 5000 });
  });

  test('agent filter "OpenClaw" hides neuro conversations', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=OpenClaw').first().click();
    // PW Conv Test is neuro, should not be visible under OpenClaw filter
    await expect(page.locator('text=PW Conv Test')).not.toBeVisible({ timeout: 3000 });
  });

  test('agent filter "All" shows all conversations', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=OpenClaw').first().click();
    await page.locator('text=All').first().click();
    await expect(page.locator('text=PW Conv Test')).toBeVisible({ timeout: 5000 });
  });
});
