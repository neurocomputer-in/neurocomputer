import { Page, expect } from '@playwright/test';

export const BASE_URL = 'http://localhost:3002';
export const API_URL = 'http://localhost:7001';

/** Wait for the app shell to be fully rendered */
export async function waitForApp(page: Page) {
  await page.goto(BASE_URL);
  // Sidebar must be visible
  await expect(page.locator('text=Projects').first()).toBeVisible({ timeout: 10000 });
}

/** Wait for conversations list to load (sidebar) */
export async function waitForConversations(page: Page) {
  await expect(page.locator('text=Conversations').first()).toBeVisible({ timeout: 8000 });
}

/** Create a project via API and return its id */
export async function apiCreateProject(name: string, color = '#8B5CF6'): Promise<string> {
  const res = await fetch(`${API_URL}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, color, description: '' }),
  });
  const data = await res.json();
  return data.id;
}

/** Delete a project via API */
export async function apiDeleteProject(id: string): Promise<void> {
  await fetch(`${API_URL}/projects/${id}`, { method: 'DELETE' });
}

/** Create a conversation via API and return its id */
export async function apiCreateConversation(
  title: string,
  agentId = 'neuro',
  projectId?: string
): Promise<string> {
  const body: Record<string, string> = { title, agent_id: agentId };
  if (projectId) body.project_id = projectId;
  const res = await fetch(`${API_URL}/conversation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return data.id;
}

/** Delete a conversation via API */
export async function apiDeleteConversation(id: string): Promise<void> {
  await fetch(`${API_URL}/conversation/${id}`, { method: 'DELETE' });
}
