import { test, expect } from '@playwright/test';
import { waitForApp, apiCreateConversation, apiDeleteConversation } from './helpers';

test.describe('F05 – Chat input & send', () => {
  let convId: string;

  test.beforeAll(async () => {
    convId = await apiCreateConversation('Chat Test', 'neuro');
  });

  test.afterAll(async () => {
    await apiDeleteConversation(convId);
  });

  test('chat input is disabled when no tab open', async ({ page }) => {
    await waitForApp(page);
    const textarea = page.locator('textarea');
    await expect(textarea).toBeDisabled();
  });

  test('chat input is enabled when a tab is open', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Chat Test').first().click();
    await page.waitForTimeout(1000);
    const textarea = page.locator('textarea');
    await expect(textarea).toBeEnabled({ timeout: 5000 });
  });

  test('can type in chat input', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Chat Test').first().click();
    await page.waitForTimeout(1000);
    await page.locator('textarea').fill('Hello from Playwright');
    await expect(page.locator('textarea')).toHaveValue('Hello from Playwright');
  });

  test('Send button disabled when input empty', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Chat Test').first().click();
    await page.waitForTimeout(1000);
    const sendBtn = page.locator('button:has-text("Send")');
    await expect(sendBtn).toBeDisabled();
  });

  test('Send button enabled when input has text', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Chat Test').first().click();
    await page.waitForTimeout(1000);
    await page.locator('textarea').fill('Hello');
    const sendBtn = page.locator('button:has-text("Send")');
    await expect(sendBtn).toBeEnabled({ timeout: 3000 });
  });

  test('pressing Enter sends message and shows user bubble', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Chat Test').first().click();
    await page.waitForTimeout(1000);
    await page.locator('textarea').fill('Playwright test message');
    await page.keyboard.press('Enter');
    // Input should clear
    await expect(page.locator('textarea')).toHaveValue('');
    // User message bubble should appear
    await expect(page.locator('text=Playwright test message')).toBeVisible({ timeout: 5000 });
  });

  test('user message bubble is right-aligned', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Chat Test').first().click();
    await page.waitForTimeout(1000);
    await page.locator('textarea').fill('Right align test');
    await page.keyboard.press('Enter');
    // User bubble has justify-content: flex-end
    const userBubble = page.locator('[style*="justify-content: flex-end"]').first();
    await expect(userBubble).toBeVisible({ timeout: 5000 });
  });

  test('loading indicator appears after sending', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Chat Test').first().click();
    await page.waitForTimeout(1000);
    await page.locator('textarea').fill('Loading indicator test');
    await page.keyboard.press('Enter');
    // Loading dots should briefly appear
    // They are tiny divs with animation — check Send button shows '...' or loading state
    const sendBtn = page.locator('button:has-text("...")');
    await expect(sendBtn).toBeVisible({ timeout: 3000 });
  });

  test('Shift+Enter adds newline without sending', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Chat Test').first().click();
    await page.waitForTimeout(1000);
    await page.locator('textarea').fill('Line one');
    await page.keyboard.press('Shift+Enter');
    await page.keyboard.type('Line two');
    await expect(page.locator('textarea')).toHaveValue('Line one\nLine two');
  });

  test('agent response arrives and appears in chat', async ({ page }) => {
    await waitForApp(page);
    await page.waitForTimeout(1500);
    await page.locator('text=Chat Test').first().click();
    await page.waitForTimeout(1000);
    await page.locator('textarea').fill('Say exactly: PONG');
    await page.keyboard.press('Enter');
    // Wait up to 20s for agent response
    const agentBubble = page.locator('[style*="background: rgba(255,255,255,0.05)"]').last();
    await expect(agentBubble).toBeVisible({ timeout: 20000 });
    // Input should be re-enabled
    await expect(page.locator('textarea')).toBeEnabled({ timeout: 20000 });
  });
});
