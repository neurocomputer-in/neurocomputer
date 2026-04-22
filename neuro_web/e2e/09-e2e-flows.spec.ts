/**
 * F09 — End-to-end user flows
 *
 * Real user journeys. Each test is a complete flow with NO page refresh
 * between steps within that flow.
 *
 * Flows:
 *   - Open conversation → send message → AI responds
 *   - Second message in same session (no refresh)
 *   - Change agent via dropdown → label updates
 *   - Switch between open tabs → history preserved
 *   - New conversation → open via sidebar → chat
 */
import { test, expect, Page } from '@playwright/test';
import { BASE_URL, apiCreateConversation, apiDeleteConversation } from './helpers';

// ── helpers ────────────────────────────────────────────────────────────────

async function loadApp(page: Page) {
  await page.goto(BASE_URL);
  await expect(page.locator('text=Projects').first()).toBeVisible({ timeout: 10000 });
  await page.waitForTimeout(1200); // let conversations poll from backend
}

async function openConversation(page: Page, title: string) {
  await page.locator(`text=${title}`).first().click();
  // Title appears in tab bar (second occurrence)
  await expect(page.locator(`text=${title}`).nth(1)).toBeVisible({ timeout: 6000 });
  // Chat input becomes usable
  await expect(page.locator('[data-testid="chat-input"]')).toBeEnabled({ timeout: 8000 });
}

async function sendMessage(page: Page, message: string) {
  const input = page.locator('[data-testid="chat-input"]');
  await input.fill(message);
  await page.keyboard.press('Enter');
  // Input clears = message sent
  await expect(input).toHaveValue('', { timeout: 3000 });
}

/**
 * Wait for AI to finish responding.
 * The chat input is disabled while isLoading; re-enabled when done.
 */
async function waitForAIResponse(page: Page, timeoutMs = 30000) {
  const input = page.locator('[data-testid="chat-input"]');
  // Goes disabled first (thinking)
  await expect(input).toBeDisabled({ timeout: 5000 });
  // Then re-enables (response arrived)
  await expect(input).toBeEnabled({ timeout: timeoutMs });
}

// ── tests ──────────────────────────────────────────────────────────────────

test.describe('F09 – End-to-end flows', () => {

  // ── Flow 1: Chat round-trip ───────────────────────────────────────────────
  test.describe('Chat: message → AI response', () => {
    let convId: string;

    test.beforeAll(async () => {
      convId = await apiCreateConversation('E2E Chat Flow', 'neuro');
    });
    test.afterAll(async () => { await apiDeleteConversation(convId); });

    test('user message shows → loading → AI response arrives', async ({ page }) => {
      await loadApp(page);
      await openConversation(page, 'E2E Chat Flow');

      await sendMessage(page, 'Say exactly: PONG');

      // User bubble appears
      await expect(page.locator('[data-testid="user-message"]').last()).toBeVisible({ timeout: 5000 });
      await expect(page.locator('text=Say exactly: PONG')).toBeVisible({ timeout: 5000 });

      // Input disabled while thinking
      await expect(page.locator('[data-testid="chat-input"]')).toBeDisabled({ timeout: 5000 });

      // AI response arrives → input re-enabled
      await expect(page.locator('[data-testid="chat-input"]')).toBeEnabled({ timeout: 30000 });

      // Agent bubble visible
      await expect(page.locator('[data-testid="agent-message"]').last()).toBeVisible({ timeout: 5000 });
    });

    test('send second message in same session without page refresh', async ({ page }) => {
      await loadApp(page);
      await openConversation(page, 'E2E Chat Flow');

      await sendMessage(page, 'Turn one');
      await waitForAIResponse(page);

      // Second message — NO page.goto(), continue in same session
      await sendMessage(page, 'Turn two');
      await expect(page.locator('text=Turn two')).toBeVisible({ timeout: 5000 });
      await waitForAIResponse(page);

      // Both messages in history
      await expect(page.locator('text=Turn one')).toBeVisible();
      await expect(page.locator('text=Turn two')).toBeVisible();
    });
  });

  // ── Flow 2: Agent change ──────────────────────────────────────────────────
  test.describe('Agent dropdown change', () => {
    test('switch Neuro → OpenClaw → back to Neuro via dropdown', async ({ page }) => {
      await loadApp(page);

      // Default label = Neuro
      await expect(page.locator('[data-testid="agent-dropdown-trigger"]')).toContainText('Neuro');

      // Open dropdown
      await page.locator('[data-testid="agent-dropdown-trigger"]').click();
      await expect(page.locator('[data-testid="agent-dropdown-menu"]')).toBeVisible({ timeout: 3000 });

      // Select OpenClaw
      await page.locator('[data-testid="agent-option-openclaw"]').click();

      // Dropdown closed, trigger now shows OpenClaw
      await expect(page.locator('[data-testid="agent-dropdown-menu"]')).not.toBeVisible({ timeout: 3000 });
      await expect(page.locator('[data-testid="agent-dropdown-trigger"]')).toContainText('OpenClaw');

      // Switch back to Neuro
      await page.locator('[data-testid="agent-dropdown-trigger"]').click();
      await page.locator('[data-testid="agent-option-neuro"]').click();
      await expect(page.locator('[data-testid="agent-dropdown-trigger"]')).toContainText('Neuro');
    });

    test('selected agent shows checkmark in open dropdown', async ({ page }) => {
      await loadApp(page);
      await page.locator('[data-testid="agent-dropdown-trigger"]').click();
      await expect(page.locator('[data-testid="agent-dropdown-menu"]')).toBeVisible({ timeout: 3000 });
      // Selected item has ✓
      await expect(page.locator('[data-testid="agent-dropdown-menu"] text=✓')).toBeVisible({ timeout: 3000 });
      // Close
      await page.keyboard.press('Escape');
    });

    test('clicking outside dropdown closes it', async ({ page }) => {
      await loadApp(page);
      await page.locator('[data-testid="agent-dropdown-trigger"]').click();
      await expect(page.locator('[data-testid="agent-dropdown-menu"]')).toBeVisible({ timeout: 3000 });
      await page.locator('body').click({ position: { x: 800, y: 500 } });
      await expect(page.locator('[data-testid="agent-dropdown-menu"]')).not.toBeVisible({ timeout: 3000 });
    });
  });

  // ── Flow 3: Multi-tab switching ───────────────────────────────────────────
  test.describe('Tab switching', () => {
    let convIdA: string;
    let convIdB: string;

    test.beforeAll(async () => {
      convIdA = await apiCreateConversation('Tab Alpha', 'neuro');
      convIdB = await apiCreateConversation('Tab Beta', 'neuro');
    });
    test.afterAll(async () => {
      await apiDeleteConversation(convIdA);
      await apiDeleteConversation(convIdB);
    });

    test('open two conversations, switch between tabs, input stays enabled', async ({ page }) => {
      await loadApp(page);
      await openConversation(page, 'Tab Alpha');

      // Open second
      await page.locator('text=Tab Beta').first().click();
      await expect(page.locator('[data-testid="chat-input"]')).toBeEnabled({ timeout: 8000 });

      // Both tabs visible in tab bar
      await expect(page.locator('text=Tab Alpha').last()).toBeVisible();
      await expect(page.locator('text=Tab Beta').last()).toBeVisible();

      // Switch back to Alpha tab
      await page.locator('text=Tab Alpha').last().click();
      await expect(page.locator('[data-testid="chat-input"]')).toBeEnabled({ timeout: 5000 });
    });

    test('message sent in Alpha persists after switching to Beta and back', async ({ page }) => {
      await loadApp(page);
      await openConversation(page, 'Tab Alpha');

      await sendMessage(page, 'Alpha unique msg');
      await expect(page.locator('text=Alpha unique msg')).toBeVisible({ timeout: 5000 });

      // Switch to Beta
      await page.locator('text=Tab Beta').first().click();
      await expect(page.locator('[data-testid="chat-input"]')).toBeEnabled({ timeout: 8000 });

      // Back to Alpha
      await page.locator('text=Tab Alpha').last().click();
      await expect(page.locator('text=Alpha unique msg')).toBeVisible({ timeout: 5000 });
    });
  });

  // ── Flow 4: New session lifecycle ─────────────────────────────────────────
  test.describe('New session', () => {
    let convId: string;

    test.afterAll(async () => {
      if (convId) await apiDeleteConversation(convId);
    });

    test('new conversation appears in sidebar, can open and chat', async ({ page }) => {
      convId = await apiCreateConversation('Fresh Session', 'neuro');
      await loadApp(page);

      // Appears in sidebar
      await expect(page.locator('text=Fresh Session')).toBeVisible({ timeout: 8000 });

      // Open it
      await openConversation(page, 'Fresh Session');

      // Send first message
      await sendMessage(page, 'First message in fresh session');
      await expect(page.locator('text=First message in fresh session')).toBeVisible({ timeout: 5000 });

      // AI responds
      await waitForAIResponse(page);

      // Agent bubble present
      await expect(page.locator('[data-testid="agent-message"]').last()).toBeVisible({ timeout: 5000 });
    });
  });
});
