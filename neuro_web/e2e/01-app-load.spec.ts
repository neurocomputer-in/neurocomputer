import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers';

test.describe('F01 – App load', () => {
  test('renders top bar with N logo', async ({ page }) => {
    await waitForApp(page);
    const logo = page.locator('text=N').first();
    await expect(logo).toBeVisible();
  });

  test('renders sidebar with Projects section', async ({ page }) => {
    await waitForApp(page);
    await expect(page.locator('text=Projects').first()).toBeVisible();
  });

  test('renders sidebar with Conversations section', async ({ page }) => {
    await waitForApp(page);
    await expect(page.locator('text=Conversations').first()).toBeVisible();
  });

  test('renders agent filter chips (All, Neuro, OpenClaw)', async ({ page }) => {
    await waitForApp(page);
    await expect(page.locator('text=All').first()).toBeVisible();
    await expect(page.locator('text=Neuro').first()).toBeVisible();
    await expect(page.locator('text=OpenClaw').first()).toBeVisible();
  });

  test('renders tab bar with + button', async ({ page }) => {
    await waitForApp(page);
    // The + button in the tab bar
    const plusBtn = page.locator('text=+').first();
    await expect(plusBtn).toBeVisible();
  });

  test('renders empty state in chat area when no tab open', async ({ page }) => {
    await waitForApp(page);
    await expect(page.locator('text=Open a conversation').first()).toBeVisible();
  });

  test('shows connection status in top bar', async ({ page }) => {
    await waitForApp(page);
    // Either "Connected", "Connecting..." or "Disconnected"
    const status = page.locator('text=/Connected|Connecting|Disconnected/').first();
    await expect(status).toBeVisible();
  });

  test('renders agent dropdown button with agent name', async ({ page }) => {
    await waitForApp(page);
    await expect(page.locator('text=Neuro').first()).toBeVisible();
  });

  test('no JS console errors on load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await waitForApp(page);
    await page.waitForTimeout(2000);
    const criticalErrors = errors.filter(e =>
      !e.includes('favicon') &&
      !e.includes('404') &&
      !e.includes('Warning:')
    );
    expect(criticalErrors, `Console errors: ${criticalErrors.join('\n')}`).toHaveLength(0);
  });
});
