'use client';
import { useState } from 'react';
import { Provider } from 'react-redux';
import { CacheProvider } from '@emotion/react';
import createCache from '@emotion/cache';
import { ChakraProvider } from '@chakra-ui/react';
import { store } from '@/store';
import { theme } from '@/theme';
import ThemeApplier from '@/theme/ThemeApplier';
import { LiveKitProvider } from '@/providers/LiveKitProvider';

function EmotionProviders({ children }: { children: React.ReactNode }) {
  const [cache] = useState(() => createCache({ key: 'css', prepend: true }));
  return (
    <CacheProvider value={cache}>
      <ChakraProvider theme={theme}>
        <ThemeApplier />
        <LiveKitProvider>
          {children}
        </LiveKitProvider>
      </ChakraProvider>
    </CacheProvider>
  );
}

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <Provider store={store}>
      <EmotionProviders>{children}</EmotionProviders>
    </Provider>
  );
}
