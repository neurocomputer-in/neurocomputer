# Neurocomputer Project Context

## Goal

Set up the neurocomputer web app for remote access via HTTPS tunnels, fix all frontend console errors, enable voice/realtime features to work from anywhere, and move workspace/project dropdowns from TopBar to side panel.

## Instructions

- `desktop-0001.neurocomputer.in` should be the backend URL, accessible from anywhere
- Web app should be accessible via its own tunnel (`web-0001.neurocomputer.in`)
- `api-0001` tunnel deleted from ingress (DNS still in CF dashboard, harmless 404)
- LiveKit voice/realtime must work over HTTPS (requires WSS)
- User prefers local LiveKit tunneled through Cloudflare over remote unencrypted LiveKit
- All services should auto-start on reboot
- **Pending**: Move workspace dropdown and project dropdown from TopBar to side panel

## Discoveries

### Project structure
`neurocomputer/` root with:
- `neurocomputer/` — Python FastAPI backend (port 7000)
- `neuro_web/` — Next.js 14 + Chakra UI v2 + Redux Toolkit (port 3000)
- `neuro_mobile/` — Android app
- `data/` — SQLite DB
- `docs/` — documentation

### Backend
- FastAPI on port 7000, has `CORSMiddleware(allow_origins=["*"])`
- Uses LiveKit for real-time data channels + voice
- WebSocket proxy patterns exist (e.g. `/ws/claude`)
- `.env` at `/home/ubuntu/neurocomputer/.env`

### Web app
- Next.js 14.2.3 App Router + Chakra UI v2 + Redux Toolkit
- Known SSR hydration issues — requires `CacheProvider` from `@emotion/react`
- `@chakra-ui/react` v2, `@emotion/react`, `@emotion/cache` all installed
- Uses `livekit-client` for real-time messaging + voice

### LiveKit
- Remote server: `ws://187.127.137.237:7880` — no TLS, can't use from HTTPS pages
- Local binary: `/home/ubuntu/bin/livekit-server`
- Local config: `/home/ubuntu/infinity_prod/livekit.yaml`
- Local keys: `***REDACTED***` / `***REDACTED***`
- Remote keys: `APIDS3JQJuquKAY` / `1Fxrrxg2jcUHrNnnBj2QqCLcFADyqWyy227iTdyHsyG`
- Media/audio uses direct UDP to public IP `45.118.156.186:50000-60000` — can't tunnel through Cloudflare
- Signaling (WSS) can be tunneled

### Cloudflare tunnels
- Tunnel ID: `45bdef16-2a3b-4fab-89c9-a1e97c274a88`
- Domain: `neurocomputer.in`
- All hostnames share one `cloudflared` process — no extra processes needed
- Cloudflared binary: `/usr/local/bin/cloudflared`
- Config: `/home/ubuntu/.cloudflared/config.yml`
- Credentials: `/home/ubuntu/.cloudflared/45bdef16-2a3b-4fab-89c9-a1e97c274a88.json`
- Systemd service exists at `/etc/systemd/system/cloudflared.service` but points to `/usr/bin/cloudflared` (wrong path, needs sudo to fix)

### Other
- Port 7000 conflict: Next.js dev sometimes grabs port 7000 instead of 3000
- Public IP: `45.118.156.186`

## Accomplished

### ✅ Tunnel setup
- Added `web-0001.neurocomputer.in` → `127.0.0.1:3000` to cloudflared config
- Added `livekit-0001.neurocomputer.in` → `127.0.0.1:7880` to cloudflared config
- Removed `api-0001.neurocomputer.in` from ingress rules
- Created DNS CNAME records for `web-0001` and `livekit-0001`
- Restarted cloudflared to pick up new config

### ✅ Local LiveKit setup
- Started `livekit-server --bind 127.0.0.1` on port 7880
- Updated `.env` to `LIVEKIT_URL=***REDACTED***` with local API keys
- Restarted backend to pick up new env

### ✅ Frontend fixes
- **Chakra SSR crash**: Added `CacheProvider` from `@emotion/react` with `createCache({ key: 'css', prepend: true })` in `providers.tsx`; moved `ColorModeScript` from `<body>` to `<head>` in `layout.tsx`; added `suppressHydrationWarning` to `<html>`
- **LiveKit mixed content**: Added `ws://` → `wss://` upgrade logic in `services/livekit.ts`, `hooks/useVoiceCall.ts`, and `services/api.ts` (terminalWsUrl). For bare IP LiveKit URLs on HTTPS pages, gracefully skips with a warning instead of crashing
- **React style collision**: Fixed `WorkspaceDropdown.tsx` — replaced `border` shorthand + `borderLeft` with individual `borderTop/Right/Bottom` + `borderLeft`
- **Redux selector warning**: Fixed `TerminalButton.tsx` — replaced `|| []` with `?? EMPTY_ARR` (module-level constant)
- **Web `.env.local`**: Set `NEXT_PUBLIC_API_URL=https://desktop-0001.neurocomputer.in`

### ✅ Auto-start
- Crontab `@reboot` entries for: cloudflared, python3 server.py, npx next dev

### ✅ CORS
- Backend already had `CORSMiddleware(allow_origins=["*"])` — confirmed working through tunnel
- The real CORS issue was backend being down (502), not missing headers

## Current tunnel config

```
# /home/ubuntu/.cloudflared/config.yml
tunnel: 45bdef16-2a3b-4fab-89c9-a1e97c274a88
credentials-file: /home/ubuntu/.cloudflared/45bdef16-2a3b-4fab-89c9-a1e97c274a88.json

ingress:
  - hostname: desktop-0001.neurocomputer.in
    service: http://127.0.0.1:7000
  - hostname: web-0001.neurocomputer.in
    service: http://127.0.0.1:3000
  - hostname: livekit-0001.neurocomputer.in
    service: http://127.0.0.1:7880
  - service: http_status:404
```

## Current .env

```
# /home/ubuntu/neurocomputer/.env
LIVEKIT_URL=***REDACTED***
LIVEKIT_API_KEY=***REDACTED***
LIVEKIT_API_SECRET=***REDACTED***
OPENAI_API_KEY=sk-proj-...
OPENCLAW_GATEWAY_TOKEN=***REDACTED***
ELEVENLABS_API_KEY=***REDACTED***
ELEVENLABS_VOICE_ID=***REDACTED***
SARVAM_API_KEY=***REDACTED***
```

## Current .env.local (web)

```
# /home/ubuntu/neurocomputer/neuro_web/.env.local
NEXT_PUBLIC_API_URL=https://desktop-0001.neurocomputer.in
```

## Crontab

```
@reboot nohup /usr/local/bin/cloudflared --no-autoupdate tunnel --config /home/ubuntu/.cloudflared/config.yml run > /tmp/cloudflared.log 2>&1 &
@reboot cd /home/ubuntu/neurocomputer/neurocomputer && nohup python3 server.py > /tmp/neuro-server.log 2>&1 &
@reboot cd /home/ubuntu/neurocomputer/neuro_web && nohup npx next dev -p 3000 > /tmp/neuro-web.log 2>&1 &
```

## Not yet done

- [ ] Move workspace dropdown and project dropdown from TopBar to side panel
- [ ] Clean up `api-0001.neurocomputer.in` DNS record (requires Cloudflare dashboard)
- [ ] Fix cloudflared systemd service path (`/usr/bin` → `/usr/local/bin`) — requires sudo
- [ ] LiveKit voice call not yet tested end-to-end
- [ ] LiveKit server not in crontab (will not survive reboot)

## Key files

| File | Purpose |
|------|---------|
| `/home/ubuntu/.cloudflared/config.yml` | Tunnel ingress routes (3 hostnames) |
| `/home/ubuntu/neurocomputer/.env` | Environment vars |
| `/home/ubuntu/neurocomputer/neuro_web/.env.local` | NEXT_PUBLIC_API_URL |
| `/home/ubuntu/neurocomputer/neuro_web/app/providers.tsx` | Emotion CacheProvider + Chakra + LiveKit providers |
| `/home/ubuntu/neurocomputer/neuro_web/app/layout.tsx` | ColorModeScript in head |
| `/home/ubuntu/neurocomputer/neuro_web/services/livekit.ts` | WSS upgrade logic |
| `/home/ubuntu/neurocomputer/neuro_web/services/api.ts` | Axios instance, BASE_URL, terminalWsUrl |
| `/home/ubuntu/neurocomputer/neuro_web/hooks/useVoiceCall.ts` | Voice call WSS upgrade |
| `/home/ubuntu/neurocomputer/neuro_web/components/layout/TopBar.tsx` | Currently has WorkspaceDropdown + ProjectDropdown (to be moved to sidebar) |
| `/home/ubuntu/neurocomputer/neuro_web/components/workspace/WorkspaceDropdown.tsx` | Workspace selector dropdown |
| `/home/ubuntu/neurocomputer/neuro_web/components/project/ProjectDropdown.tsx` | Project selector dropdown |
| `/home/ubuntu/neurocomputer/neuro_web/components/terminal/TerminalButton.tsx` | Terminal dropdown |
| `/home/ubuntu/neurocomputer/neuro_web/providers/LiveKitProvider.tsx` | LiveKit context + Redux |
| `/home/ubuntu/neurocomputer/neuro_web/store/` | Redux slices (uiSlice, conversationSlice, chatSlice, workspaceSlice, etc.) |
| `/home/ubuntu/neurocomputer/neuro_web/theme/` | Chakra theme + presets + ThemeApplier |
| `/home/ubuntu/neurocomputer/neurocomputer/server.py` | FastAPI backend |
| `/home/ubuntu/neurocomputer/neurocomputer/core/chat_handler.py` | LiveKit token gen, LIVEKIT_URL |
| `/home/ubuntu/infinity_prod/livekit.yaml` | Local LiveKit config |
| `/home/ubuntu/neurocomputer/neuro_web/electron/main.js` | Electron desktop wrapper |
