# neuro_web PWA Android Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make neuro_web installable on Android via Chrome as a fullscreen PWA.

**Architecture:** `@ducanh2912/next-pwa` wraps `next.config.js` and auto-generates a Workbox service worker at build time. A `manifest.json` declares the app identity with `display: fullscreen`. Static assets are cached; all API/backend calls are network-only.

**Tech Stack:** Next.js 14, @ducanh2912/next-pwa, Workbox (via plugin), TypeScript

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `neuro_web/package.json` | Modify | Add `@ducanh2912/next-pwa` dependency |
| `neuro_web/.gitignore` | Modify | Exclude generated `sw.js`, `workbox-*.js` |
| `neuro_web/next.config.js` | Modify | Wrap config with `withPWA()` |
| `neuro_web/public/manifest.json` | Create | PWA identity, icons, fullscreen display |
| `neuro_web/public/icons/icon-192.png` | Create | 192×192 placeholder app icon |
| `neuro_web/public/icons/icon-512.png` | Create | 512×512 placeholder app icon |
| `neuro_web/app/layout.tsx` | Modify | Add manifest link + theme-color meta tag |
| `neuro_web/scripts/generate-icons.mjs` | Create | One-time script to generate placeholder PNGs |

---

## Task 1: Install dependency and update .gitignore

**Files:**
- Modify: `neuro_web/package.json`
- Modify: `neuro_web/.gitignore`

- [ ] **Step 1: Install @ducanh2912/next-pwa**

```bash
cd neuro_web && npm install @ducanh2912/next-pwa
```

Expected: `package.json` updated, `package-lock.json` updated, no errors.

- [ ] **Step 2: Add generated files to .gitignore**

In `neuro_web/.gitignore`, append after the existing TypeScript section:

```
# PWA generated files
public/sw.js
public/sw.js.map
public/workbox-*.js
public/workbox-*.js.map
```

- [ ] **Step 3: Commit**

```bash
cd neuro_web && git add package.json package-lock.json .gitignore
git commit -m "chore(pwa): install @ducanh2912/next-pwa"
```

---

## Task 2: Create PWA manifest

**Files:**
- Create: `neuro_web/public/manifest.json`

- [ ] **Step 1: Create manifest.json**

Create `neuro_web/public/manifest.json` with this exact content:

```json
{
  "name": "Neurocomputer",
  "short_name": "Neuro",
  "description": "Multi-agent AI workspace",
  "start_url": "/",
  "display": "fullscreen",
  "orientation": "any",
  "background_color": "#0a0a0a",
  "theme_color": "#0a0a0a",
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ]
}
```

- [ ] **Step 2: Verify JSON is valid**

```bash
node -e "JSON.parse(require('fs').readFileSync('neuro_web/public/manifest.json','utf8')); console.log('valid')"
```

Expected output: `valid`

- [ ] **Step 3: Commit**

```bash
git add neuro_web/public/manifest.json
git commit -m "feat(pwa): add web app manifest with fullscreen display"
```

---

## Task 3: Generate placeholder icons

**Files:**
- Create: `neuro_web/scripts/generate-icons.mjs`
- Create: `neuro_web/public/icons/icon-192.png`
- Create: `neuro_web/public/icons/icon-512.png`

- [ ] **Step 1: Create icons directory**

```bash
mkdir -p neuro_web/public/icons
```

- [ ] **Step 2: Create icon generation script**

Create `neuro_web/scripts/generate-icons.mjs`:

```js
import sharp from 'sharp';
import { mkdirSync } from 'fs';

mkdirSync('public/icons', { recursive: true });

const sizes = [192, 512];

for (const size of sizes) {
  await sharp({
    create: {
      width: size,
      height: size,
      channels: 4,
      background: { r: 10, g: 10, b: 10, alpha: 1 },
    },
  })
    .composite([
      {
        input: Buffer.from(
          `<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
            <circle cx="${size / 2}" cy="${size / 2}" r="${size * 0.35}" fill="none" stroke="#7c3aed" stroke-width="${size * 0.06}"/>
            <circle cx="${size / 2}" cy="${size / 2}" r="${size * 0.12}" fill="#7c3aed"/>
          </svg>`
        ),
        top: 0,
        left: 0,
      },
    ])
    .png()
    .toFile(`public/icons/icon-${size}.png`);

  console.log(`Generated icon-${size}.png`);
}
```

- [ ] **Step 3: Run the script**

```bash
cd neuro_web && node scripts/generate-icons.mjs
```

Expected output:
```
Generated icon-192.png
Generated icon-512.png
```

If `sharp` is not installed: `npm install --save-dev sharp` then re-run.

- [ ] **Step 4: Verify icons exist**

```bash
ls -lh neuro_web/public/icons/
```

Expected: two PNG files, each > 1KB.

- [ ] **Step 5: Commit**

```bash
git add neuro_web/public/icons/ neuro_web/scripts/generate-icons.mjs
git commit -m "feat(pwa): add placeholder app icons (192px, 512px)"
```

---

## Task 4: Wrap next.config.js with withPWA

**Files:**
- Modify: `neuro_web/next.config.js`

Current content of `neuro_web/next.config.js`:
```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // false to avoid double-mounting LiveKit connections
};
module.exports = nextConfig;
```

- [ ] **Step 1: Update next.config.js**

Replace the entire content of `neuro_web/next.config.js` with:

```js
const withPWA = require('@ducanh2912/next-pwa').default;

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // false to avoid double-mounting LiveKit connections
};

module.exports = withPWA({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  runtimeCaching: [
    {
      urlPattern: /^https?:\/\/.*\/api\/.*/i,
      handler: 'NetworkOnly',
    },
    {
      urlPattern: /^https?:\/\/localhost:7000\/.*/i,
      handler: 'NetworkOnly',
    },
    {
      urlPattern: /\/_next\/static\/.*/i,
      handler: 'CacheFirst',
      options: {
        cacheName: 'next-static',
        expiration: { maxEntries: 200, maxAgeSeconds: 30 * 24 * 60 * 60 },
      },
    },
    {
      urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/i,
      handler: 'CacheFirst',
      options: {
        cacheName: 'images',
        expiration: { maxEntries: 64, maxAgeSeconds: 30 * 24 * 60 * 60 },
      },
    },
  ],
})(nextConfig);
```

- [ ] **Step 2: Verify config syntax**

```bash
cd neuro_web && node -e "require('./next.config.js'); console.log('valid')"
```

Expected output: `valid`

- [ ] **Step 3: Commit**

```bash
git add neuro_web/next.config.js
git commit -m "feat(pwa): configure withPWA — network-only for API, cache-first for static"
```

---

## Task 5: Update layout.tsx with manifest link and theme-color

**Files:**
- Modify: `neuro_web/app/layout.tsx`

- [ ] **Step 1: Update layout.tsx**

Replace the `<head>` block in `neuro_web/app/layout.tsx`. The file currently has:

```tsx
      <head>
        <link rel="preconnect" href="https://rsms.me/" />
        <link rel="stylesheet" href="https://rsms.me/inter/inter.css" />
        <ColorModeScript initialColorMode="dark" />
      </head>
```

Replace it with:

```tsx
      <head>
        <link rel="preconnect" href="https://rsms.me/" />
        <link rel="stylesheet" href="https://rsms.me/inter/inter.css" />
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#0a0a0a" />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
        <ColorModeScript initialColorMode="dark" />
      </head>
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/app/layout.tsx
git commit -m "feat(pwa): add manifest link and theme-color to layout"
```

---

## Task 6: Build and verify PWA

- [ ] **Step 1: Run production build**

```bash
cd neuro_web && npm run build
```

Expected: build succeeds. You should see near the end:
```
✓ Compiled successfully
```
Also confirm these files were generated:
```bash
ls neuro_web/public/sw.js neuro_web/public/workbox-*.js
```
Expected: both exist.

- [ ] **Step 2: Serve production build**

```bash
cd neuro_web && npm run start
```

Expected: server starts on port 3000 (or configured port).

- [ ] **Step 3: Verify manifest in Chrome DevTools**

Open Chrome → `http://localhost:3000` → DevTools (F12) → Application tab → Manifest.

Confirm:
- Name shows "Neurocomputer"
- Display shows "fullscreen"
- Both icons (192, 512) load without errors
- No manifest parse errors shown

- [ ] **Step 4: Verify service worker registered**

In Chrome DevTools → Application → Service Workers.

Confirm:
- `sw.js` shows as "Activated and running"
- Source shows the local URL

- [ ] **Step 5: Run Lighthouse PWA audit**

In Chrome DevTools → Lighthouse tab → select "Progressive Web App" category → Analyze page load.

Expected: PWA installability checks pass (no red X on "installable" criteria). Score 80+ is acceptable for this stage; icon and HTTPS warnings are expected in local dev.

- [ ] **Step 6: Final commit if any cleanup needed**

```bash
git add -p  # stage only intentional changes
git commit -m "chore(pwa): build verification cleanup"
```

---

## Verification Checklist

After all tasks complete, confirm:

- [ ] `npm run build` succeeds with no errors
- [ ] `public/sw.js` exists after build (and is in .gitignore)
- [ ] Chrome DevTools → Application → Manifest loads without errors
- [ ] `display: fullscreen` shown in manifest panel
- [ ] Service worker activated in Chrome DevTools
- [ ] On Android Chrome: visiting the URL shows "Add to Home Screen" banner or it's available via Chrome menu → "Install app"
- [ ] After install, tapping app icon opens in fullscreen (no browser address bar)
