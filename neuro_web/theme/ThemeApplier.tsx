'use client';
import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setTheme } from '@/store/uiSlice';
import { getTheme } from './presets';

/**
 * Reads the current workspace's theme id from Redux and writes its token
 * set as CSS variables on ``document.documentElement``. Any component can
 * then use ``color: var(--accent)`` / ``background: var(--surface)`` /
 * etc. and automatically respect the active workspace's theme.
 *
 * Also exposes the wallpaper id via ``uiSlice.theme`` (kept in sync) so
 * the existing ``<ThreeBackground />`` picks the matching 3D scene
 * without refactoring.
 */
export default function ThemeApplier() {
  const dispatch = useAppDispatch();
  const workspaces = useAppSelector(s => s.workspace.workspaces);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);

  const activeWorkspace = workspaces.find(w => w.id === selectedWorkspaceId);
  const themeId = activeWorkspace?.theme;
  const theme = getTheme(themeId);

  useEffect(() => {
    const root = document.documentElement;
    const t = theme.tokens;
    root.style.setProperty('--accent', t.accent);
    root.style.setProperty('--accent-hover', t.accentHover);
    root.style.setProperty('--accent-soft', t.accentSoft);
    root.style.setProperty('--accent-border', t.accentBorder);
    root.style.setProperty('--bg', t.bg);
    root.style.setProperty('--surface', t.surface);
    root.style.setProperty('--border', t.border);
    root.style.setProperty('--text', t.text);
    root.style.setProperty('--text-dim', t.textDim);
    root.style.setProperty('--text-muted', t.textMuted);
    root.setAttribute('data-theme', theme.id);
    root.setAttribute('data-wallpaper', t.wallpaper);
    // Mirror wallpaper id into uiSlice.theme so the existing
    // ThreeBackground component (which still reads uiSlice.theme) picks
    // the matching 3D scene without refactor.
    dispatch(setTheme(t.wallpaper as any));
  }, [theme, dispatch]);

  return null;
}
