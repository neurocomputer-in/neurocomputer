import type { Metadata, Viewport } from 'next';
import { ColorModeScript } from '@chakra-ui/react';
import './globals.css';
import Providers from './providers';

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
  interactiveWidget: 'resizes-content',
};

export const metadata: Metadata = {
  title: 'Neuro',
  description: 'Multi-agent AI workspace',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" style={{ height: '100%' }} suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://rsms.me/" />
        <link rel="stylesheet" href="https://rsms.me/inter/inter.css" />
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#0a0a0a" />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
        <ColorModeScript initialColorMode="dark" />
      </head>
      <body style={{ height: '100%', overflow: 'hidden' }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
