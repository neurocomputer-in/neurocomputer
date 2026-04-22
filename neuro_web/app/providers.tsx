'use client';
import { Provider } from 'react-redux';
import { ChakraProvider, ColorModeScript } from '@chakra-ui/react';
import { store } from '@/store';
import { theme } from '@/theme';
import ThemeApplier from '@/theme/ThemeApplier';
import { LiveKitProvider } from '@/providers/LiveKitProvider';

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <Provider store={store}>
      <ColorModeScript initialColorMode="dark" />
      <ChakraProvider theme={theme}>
        <ThemeApplier />
        <LiveKitProvider>
          {children}
        </LiveKitProvider>
      </ChakraProvider>
    </Provider>
  );
}
