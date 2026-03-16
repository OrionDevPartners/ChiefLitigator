/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable source maps in production — users cannot see source code
  productionBrowserSourceMaps: false,

  // Strip console.log in production
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },

  // Hide framework identity
  poweredByHeader: false,

  // Security headers on every response
  async headers() {
    return [{
      source: '/(.*)',
      headers: [
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'X-XSS-Protection', value: '1; mode=block' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
      ],
    }]
  },

  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.optimization.minimize = true
    }
    return config
  },
}

module.exports = nextConfig
