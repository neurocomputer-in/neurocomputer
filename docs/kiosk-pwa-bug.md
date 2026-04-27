# Remote-Desktop Kiosk Mode Fails on Android Chrome PWA

## Symptom

In the Neuro web app's **Remote Desktop** tab on mobile, the user enters
"kiosk mode" so the desktop video stream covers the entire viewport with a
glowing border. Chrome (top app-bar with logo / workspace / projects / theme,
window-tab strip, bottom dock) is supposed to disappear.

| Environment | Result |
|-------------|--------|
| Chrome DevTools mobile emulation (desktop browser) | ✅ Works — chrome hides correctly, stays hidden |
| Mobile Chrome (Android phone, NOT installed) | ✅ Works |
| Installed PWA on Android (Add to Home Screen) | ❌ **Chrome briefly hides, then reappears** |

User has tried:

- Cleared all Chrome data for the origin (`web-0001.…`)
- Removed home-screen shortcut and re-added it via Chrome menu → Open Neuro
- Confirmed the phone is on Chrome (not Samsung Internet / Firefox)

Same code, same DOM, same React tree — only the install/launch context differs.

## Architecture Summary

When the user enters kiosk mode:

1. Redux `mobileDesktop.kioskActive` flips to `true`.
2. `DesktopApp.tsx` re-renders with `createPortal(content, document.body)` —
   escaping any transformed/stacking ancestors so its `position: fixed;
   inset: 0; z-index: 9999` truly covers the viewport.
3. `<body>` gets the class `desktop-kiosk` (added in a `useEffect`).
4. Every chrome element is tagged `className="neuro-chrome"` and hidden by:
   - **React conditional**: `{!desktopKioskActive && <Chrome />}` — element
     is not rendered at all.
   - **CSS belt-and-braces** in `globals.css`:
     ```css
     body.desktop-kiosk .neuro-chrome { display: none !important; }
     ```
5. `requestFullscreen({ navigationUI: 'hide' })` is called as a side effect
   (best-effort — kiosk doesn't depend on it succeeding).
6. A capture-phase `pointerdown` listener re-requests fullscreen on every
   tap if the OS dropped it (handles Android's edge-swipe revealing system bars).

## What's Verified

Headless Playwright at viewport 900×400 (matches an Android phone in landscape,
which falls in the desktop-shell branch because viewport > 767):

```
bodyKioskClass: true
chromeElCount: 1  (Window title bar div, with neuro-chrome class)
visibleChromeCount: 0  (CSS rule hides it)
```

→ React conditional rendering works, body class is set, CSS hiding works.
DOM is correct. Yet on the real PWA the user reports chrome reappears.

## Hypotheses (Unconfirmed)

1. **Android system bars, not our chrome.** Even with manifest `display:
   fullscreen` + `display_override: ["fullscreen", "standalone", "minimal-ui"]`,
   some Android versions/Chrome versions ignore it for installed PWAs and
   show the system status bar (top) and nav bar (bottom) anyway. User says
   what they see has "neuro logo, workspace, all projects, theme change
   buttons" — those words match our MenuBar, not Android system UI — so this
   may not be the cause, but worth ruling out.
2. **PWA-specific lifecycle event** that re-mounts `DesktopApp` and runs the
   cleanup `dispatch(setKioskActive(false))`. Possible triggers: orientation
   lock attempt firing an orientation-change that re-rendered the page-level
   shell, visibilitychange when entering Android immersive, etc.
3. **Redux state not propagating** in PWA-standalone for some reason
   (unlikely but possible if the install bundled an older client).

## Files Involved

- `/home/ubuntu/neurocomputer/neuro_web/components/mobile-desktop/DesktopApp.tsx`
  — outer container, portal, body class effect, pointerdown re-request.
- `/home/ubuntu/neurocomputer/neuro_web/components/mobile-desktop/FloatingToolbar.tsx`
  — Fullscreen button (kiosk toggle now Redux-driven, not
  `document.fullscreenElement`-driven).
- `/home/ubuntu/neurocomputer/neuro_web/components/mobile-desktop/TapToConnectOverlay.tsx`
  — first-tap entry on mobile shell; dismissal driven by Redux.
- `/home/ubuntu/neurocomputer/neuro_web/components/os/Window.tsx`
  — Window title bar tagged `neuro-chrome`.
- `/home/ubuntu/neurocomputer/neuro_web/app/page.tsx`
  — both shells gate `MenuBar` / `Sidebar` / `MobileTabStrip` / dock-toggle /
  `Dock` on `!desktopKioskActive`.
- `/home/ubuntu/neurocomputer/neuro_web/app/globals.css`
  — `body.desktop-kiosk .neuro-chrome { display: none !important; }`.
- `/home/ubuntu/neurocomputer/neuro_web/app/layout.tsx`
  — meta tags: `mobile-web-app-capable: yes`,
  `apple-mobile-web-app-capable: yes`,
  `apple-mobile-web-app-status-bar-style: black-translucent`.
- `/home/ubuntu/neurocomputer/neuro_web/store/mobileDesktopSlice.ts`
  — `kioskActive` state + `setKioskActive` action.
- `/home/ubuntu/neurocomputer/neuro_web/public/manifest.json`
  — `display: fullscreen`, `display_override: ["fullscreen", "standalone",
  "minimal-ui"]`.

## Next Diagnostic Step

Need a screenshot of the actual PWA on the user's phone showing what's
visible after entering kiosk. The exact pixels of the visible bars will tell
us whether they're our React chrome (bug in our code that DevTools doesn't
reproduce) or Android system UI (manifest / OS-level immersive issue).
