/**
 * Theme presets — per-workspace UI + 3D-wallpaper tokens.
 *
 * Each theme is a flat object of design tokens. ``ThemeApplier`` writes
 * these as CSS variables on ``document.documentElement``, so every
 * component can pick up the active theme via ``var(--accent)`` etc.
 * The ``wallpaper`` id maps to a 3D scene under
 * ``components/three/themes/*``.
 *
 * To add a theme: append an entry to ``THEMES`` below — no other file
 * needs to change.
 */

export type ThemeId =
  | 'cosmic'
  | 'forest'
  | 'sunset'
  | 'ocean'
  | 'minimal'
  | 'amber';

export interface ThemeTokens {
  /** Matches a folder name under ``components/three/themes/``. */
  wallpaper: 'neural-network' | 'deep-space' | 'digital-rain' | 'minimal-dark';
  /** Primary brand colour — interactive elements, focus rings. */
  accent: string;
  /** Hover variant of accent. */
  accentHover: string;
  /** Soft accent background (e.g. pill hover, selected tab). */
  accentSoft: string;
  /** Subtle border for accented elements. */
  accentBorder: string;
  /** Neutral page/base background (under the 3D wallpaper overlay). */
  bg: string;
  /** Dim translucent surface used for panels. */
  surface: string;
  /** Border colour for surfaces. */
  border: string;
  /** Primary text. */
  text: string;
  /** Secondary/dim text. */
  textDim: string;
  /** Muted/placeholder text. */
  textMuted: string;
}

export interface ThemeMeta {
  id: ThemeId;
  label: string;
  description: string;
  /** Single swatch colour used in pickers. */
  swatch: string;
  tokens: ThemeTokens;
}

export const THEMES: Record<ThemeId, ThemeMeta> = {
  cosmic: {
    id: 'cosmic',
    label: 'Cosmic',
    description: 'Deep violet with neural-network wallpaper',
    swatch: '#7170ff',
    tokens: {
      wallpaper:    'neural-network',
      accent:       '#7170ff',
      accentHover:  '#8b7aff',
      accentSoft:   'rgba(113,112,255,0.12)',
      accentBorder: 'rgba(113,112,255,0.25)',
      bg:           '#0a0a0b',
      surface:      'rgba(255,255,255,0.02)',
      border:       'rgba(255,255,255,0.08)',
      text:         '#f7f8f8',
      textDim:      '#8a8f98',
      textMuted:    '#62666d',
    },
  },
  ocean: {
    id: 'ocean',
    label: 'Ocean',
    description: 'Cool cyan with deep-space wallpaper',
    swatch: '#14B8A6',
    tokens: {
      wallpaper:    'deep-space',
      accent:       '#14B8A6',
      accentHover:  '#2dd4bf',
      accentSoft:   'rgba(20,184,166,0.12)',
      accentBorder: 'rgba(20,184,166,0.25)',
      bg:           '#071014',
      surface:      'rgba(255,255,255,0.02)',
      border:       'rgba(255,255,255,0.07)',
      text:         '#f2fafa',
      textDim:      '#7ea3a3',
      textMuted:    '#536b6b',
    },
  },
  forest: {
    id: 'forest',
    label: 'Forest',
    description: 'Matrix green with digital-rain wallpaper',
    swatch: '#22C55E',
    tokens: {
      wallpaper:    'digital-rain',
      accent:       '#22C55E',
      accentHover:  '#34d874',
      accentSoft:   'rgba(34,197,94,0.12)',
      accentBorder: 'rgba(34,197,94,0.25)',
      bg:           '#07100a',
      surface:      'rgba(255,255,255,0.02)',
      border:       'rgba(255,255,255,0.07)',
      text:         '#f2fbf5',
      textDim:      '#7ea394',
      textMuted:    '#536b60',
    },
  },
  sunset: {
    id: 'sunset',
    label: 'Sunset',
    description: 'Warm amber with deep-space wallpaper',
    swatch: '#F97316',
    tokens: {
      wallpaper:    'deep-space',
      accent:       '#F97316',
      accentHover:  '#fb8d3b',
      accentSoft:   'rgba(249,115,22,0.12)',
      accentBorder: 'rgba(249,115,22,0.25)',
      bg:           '#110a07',
      surface:      'rgba(255,255,255,0.02)',
      border:       'rgba(255,255,255,0.07)',
      text:         '#fbf6f2',
      textDim:      '#a39087',
      textMuted:    '#6b5a51',
    },
  },
  amber: {
    id: 'amber',
    label: 'Amber',
    description: 'Golden accent with minimal wallpaper',
    swatch: '#F59E0B',
    tokens: {
      wallpaper:    'minimal-dark',
      accent:       '#F59E0B',
      accentHover:  '#fbbf24',
      accentSoft:   'rgba(245,158,11,0.12)',
      accentBorder: 'rgba(245,158,11,0.25)',
      bg:           '#0d0b07',
      surface:      'rgba(255,255,255,0.02)',
      border:       'rgba(255,255,255,0.07)',
      text:         '#f9f7f1',
      textDim:      '#a39a87',
      textMuted:    '#6b6151',
    },
  },
  minimal: {
    id: 'minimal',
    label: 'Minimal',
    description: 'Neutral indigo with minimal wallpaper',
    swatch: '#5e6ad2',
    tokens: {
      wallpaper:    'minimal-dark',
      accent:       '#5e6ad2',
      accentHover:  '#6b77de',
      accentSoft:   'rgba(94,106,210,0.12)',
      accentBorder: 'rgba(94,106,210,0.25)',
      bg:           '#0a0a0b',
      surface:      'rgba(255,255,255,0.02)',
      border:       'rgba(255,255,255,0.08)',
      text:         '#f7f8f8',
      textDim:      '#8a8f98',
      textMuted:    '#62666d',
    },
  },
};

export const THEME_LIST: ThemeMeta[] = Object.values(THEMES);
export const DEFAULT_THEME: ThemeId = 'cosmic';

export function getTheme(id: string | undefined | null): ThemeMeta {
  return (id && THEMES[id as ThemeId]) || THEMES[DEFAULT_THEME];
}
