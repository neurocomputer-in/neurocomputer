import { test, expect } from '@playwright/test';
import { waitForApp, apiDeleteProject, API_URL } from './helpers';

test.describe('F02 – Projects', () => {
  test('loads project list from API on startup', async ({ page }) => {
    await waitForApp(page);
    // "NoProject" always appears in sidebar
    await expect(page.locator('text=NoProject')).toBeVisible({ timeout: 8000 });
  });

  test('+ button opens create project modal', async ({ page }) => {
    await waitForApp(page);
    // Click the + next to "Projects" label
    const projectsSection = page.locator('text=PROJECTS').first();
    // The + is a sibling element — click the + visible near top of sidebar
    await page.locator('text=PROJECTS').first().locator('..').locator('text=+').click();
    await expect(page.locator('text=New Project')).toBeVisible();
  });

  test('can type project name in create modal', async ({ page }) => {
    await waitForApp(page);
    await page.locator('text=PROJECTS').first().locator('..').locator('text=+').click();
    await expect(page.locator('text=New Project')).toBeVisible();
    const input = page.locator('input[placeholder="Project name"]');
    await input.fill('Test Project PW');
    await expect(input).toHaveValue('Test Project PW');
  });

  test('can select a color in create modal', async ({ page }) => {
    await waitForApp(page);
    await page.locator('text=PROJECTS').first().locator('..').locator('text=+').click();
    await expect(page.locator('text=Color')).toBeVisible();
    // Color circles are rendered as small divs — click the second one (amber)
    const colorPicker = page.locator('text=Color').locator('..').locator('div[style*="border-radius: 50%"]').nth(1);
    await colorPicker.click();
  });

  test('Create button is disabled when name empty', async ({ page }) => {
    await waitForApp(page);
    await page.locator('text=PROJECTS').first().locator('..').locator('text=+').click();
    const createBtn = page.locator('button:has-text("Create")');
    await expect(createBtn).toBeDisabled();
  });

  test('can create a new project', async ({ page }) => {
    await waitForApp(page);
    await page.locator('text=PROJECTS').first().locator('..').locator('text=+').click();
    await page.locator('input[placeholder="Project name"]').fill('PW Test Project');
    await page.locator('button:has-text("Create")').click();
    // Modal closes and new project appears in sidebar
    await expect(page.locator('text=PW Test Project')).toBeVisible({ timeout: 5000 });
    // Cleanup
    const res = await fetch(`${API_URL}/projects`);
    const projects = await res.json();
    const proj = projects.find((p: { name: string; id: string }) => p.name === 'PW Test Project');
    if (proj) await apiDeleteProject(proj.id);
  });

  test('Escape closes create modal', async ({ page }) => {
    await waitForApp(page);
    await page.locator('text=PROJECTS').first().locator('..').locator('text=+').click();
    await expect(page.locator('text=New Project')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.locator('text=New Project')).not.toBeVisible();
  });

  test('clicking a project filters conversation list', async ({ page }) => {
    await waitForApp(page);
    // Click NoProject
    await page.locator('text=NoProject').click();
    await page.waitForTimeout(1000);
    // Conversations section should still be visible after selection
    await expect(page.locator('text=Conversations').first()).toBeVisible();
  });

  test('right-click project shows context menu', async ({ page }) => {
    // Create a project first
    const res = await fetch(`${API_URL}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'RightClick Test', color: '#8B5CF6' }),
    });
    const proj = await res.json();

    await waitForApp(page);
    await page.waitForTimeout(1000); // wait for projects to load

    await page.locator(`text=RightClick Test`).click({ button: 'right' });
    await expect(page.locator('text=Rename')).toBeVisible();
    await expect(page.locator('text=Delete')).toBeVisible();

    await page.keyboard.press('Escape');
    await apiDeleteProject(proj.id);
  });
});
