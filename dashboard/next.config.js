/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/backend/:path*',
        destination: `${process.env.BACKEND_URL || (process.env.NODE_ENV === 'production' ? 'https://ichapterwise.com' : 'http://localhost:8000')}/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
