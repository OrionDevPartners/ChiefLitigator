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

  // Security headers on every response — stricter for admin panel
  async headers() {
    return [{
      source: '/(.*)',
      headers: [
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'X-XSS-Protection', value: '1; mode=block' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        { key: 'Content-Security-Policy', value: "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://api.cyphergy.ai; frame-ancestors 'none';" },
        { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
        { key: 'Cross-Origin-Opener-Policy', value: 'same-origin' },
        { key: 'Cross-Origin-Resource-Policy', value: 'same-origin' },
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
