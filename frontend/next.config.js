/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export for single-service deployment (Django serves static HTML)
  output: 'export',

  // Serve Next.js assets from Django's /static/ path
  // This makes /_next/static/* → /static/_next/static/*
  assetPrefix: '/static',

  reactStrictMode: true,
  swcMinify: true,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'res.cloudinary.com',
        pathname: '/**',
      },
    ],
    // Unoptimized required for static export
    unoptimized: true,
  },
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL || 'https://slbookingsystem.onrender.com/api',
  },
}

module.exports = nextConfig
