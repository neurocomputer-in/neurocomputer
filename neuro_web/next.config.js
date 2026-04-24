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
