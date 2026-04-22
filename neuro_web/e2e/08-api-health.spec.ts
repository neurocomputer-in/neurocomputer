import { test, expect } from '@playwright/test';
import { API_URL } from './helpers';

test.describe('F08 – Backend API health', () => {
  test('GET /health returns 200', async ({ request }) => {
    const res = await request.get(`${API_URL}/health`);
    expect(res.status()).toBe(200);
  });

  test('GET /projects returns array', async ({ request }) => {
    const res = await request.get(`${API_URL}/projects`);
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test('GET /conversations returns array', async ({ request }) => {
    const res = await request.get(`${API_URL}/conversations`);
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test('POST /conversation creates and returns conversation', async ({ request }) => {
    const res = await request.post(`${API_URL}/conversation`, {
      data: { title: 'API Health Test', agent_id: 'neuro' },
    });
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data.id).toBeTruthy();
    expect(data.title).toBe('API Health Test');
    // cleanup
    await request.delete(`${API_URL}/conversation/${data.id}`);
  });

  test('POST /chat/token returns token and url', async ({ request }) => {
    // Create conv first
    const convRes = await request.post(`${API_URL}/conversation`, {
      data: { title: 'Token Test' },
    });
    const conv = await convRes.json();

    const tokenRes = await request.post(`${API_URL}/chat/token`, {
      data: { conversation_id: conv.id },
    });
    expect(tokenRes.status()).toBe(200);
    const tokenData = await tokenRes.json();
    expect(tokenData.token).toBeTruthy();
    expect(tokenData.url).toBeTruthy();

    await request.delete(`${API_URL}/conversation/${conv.id}`);
  });

  test('POST /chat/send accepts message', async ({ request }) => {
    const convRes = await request.post(`${API_URL}/conversation`, {
      data: { title: 'Send Test' },
    });
    const conv = await convRes.json();

    const sendRes = await request.post(`${API_URL}/chat/send`, {
      data: { conversation_id: conv.id, message: 'ping', agent_id: 'neuro' },
    });
    expect(sendRes.status()).toBe(200);

    await request.delete(`${API_URL}/conversation/${conv.id}`);
  });

  test('GET /agents/types returns agent list', async ({ request }) => {
    const res = await request.get(`${API_URL}/agents/types`);
    expect(res.status()).toBe(200);
  });
});
