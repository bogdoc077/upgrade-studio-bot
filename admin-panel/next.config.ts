import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  
  // Configure API routes to accept larger file uploads
  experimental: {
    serverActions: {
      bodySizeLimit: '50mb',
    },
  },
  
  // Proxy API requests to FastAPI backend
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8001/:path*',
      },
    ];
  },
};

export default nextConfig;
