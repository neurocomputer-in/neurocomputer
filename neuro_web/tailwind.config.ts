import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './hooks/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        'bg-deep': '#08090a',
        'bg-panel': '#0f1011',
        'bg-surface': '#191a1b',
        'bg-elevated': '#28282c',
        brand: '#5e6ad2',
        accent: '#7170ff',
        'accent-hover': '#828fff',
        'text-primary': '#f7f8f8',
        'text-secondary': '#d0d6e0',
        'text-tertiary': '#8a8f98',
        'text-quaternary': '#62666d',
        success: '#27a644',
        warning: '#f59e0b',
        error: '#ef4444',
      },
    },
  },
  plugins: [],
};
export default config;
