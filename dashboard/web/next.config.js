/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',  // For Vercel deployment
  
  // 环境变量
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  
  // API 重写规则
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
  
  // 图片域名白名单
  images: {
    domains: ['154.26.181.47'],
  },
}

module.exports = nextConfig
