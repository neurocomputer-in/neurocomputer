import { extendTheme } from '@chakra-ui/react';

export const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  colors: {
    brand: {
      50: '#e8eaff',
      100: '#c5c9ff',
      200: '#9ea4ff',
      300: '#828fff',
      400: '#7170ff',
      500: '#5e6ad2',
      600: '#4e59b8',
      700: '#3e479e',
      800: '#2e3584',
      900: '#1e236a',
    },
    bg: {
      deep: '#08090a',
      panel: '#0f1011',
      surface: '#191a1b',
      elevated: '#28282c',
    },
    textColor: {
      primary: '#f7f8f8',
      secondary: '#d0d6e0',
      tertiary: '#8a8f98',
      quaternary: '#62666d',
    },
  },
  styles: {
    global: {
      body: {
        bg: '#08090a',
        color: '#f7f8f8',
        fontFamily: "'Inter Variable', 'Inter', 'SF Pro Display', -apple-system, system-ui, sans-serif",
        fontFeatureSettings: '"cv01", "ss03"',
      },
      '*': { boxSizing: 'border-box' },
      '::-webkit-scrollbar': { width: '4px' },
      '::-webkit-scrollbar-track': { background: 'transparent' },
      '::-webkit-scrollbar-thumb': { background: '#23252a', borderRadius: '4px' },
    },
  },
  components: {
    Button: {
      defaultProps: { colorScheme: 'brand' },
    },
  },
});
