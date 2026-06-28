/** @type {import('next').NextConfig} */
const nextConfig = {
  // API do backend Manolo (Render)
  // Em produção: NEXT_PUBLIC_API_URL=https://seu-backend.onrender.com
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  // Rewrite para evitar CORS no desenvolvimento local (proxeia /api/* para o backend)
  async rewrites() {
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
        },
      ]
    }
    return []
  },
}

module.exports = nextConfig
