import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Turbopack configuration (enabled by default in Next.js 16)
  turbopack: {
    root: process.cwd(),
  },
  
  // Experimental features for performance
  experimental: {
    optimizePackageImports: ['lucide-react', 'framer-motion'],
    // optimizeCss: true, // Temporarily disabled due to critters issue
  },
  
  // Image optimization
  images: {
    formats: ['image/webp', 'image/avif'],
    minimumCacheTTL: 31536000,
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
        port: '',
        pathname: '/**',
      },
    ],
  },
  
  // Compression and optimization
  compress: true,
  
  // PoweredByHeader removal for security and speed
  poweredByHeader: false,
  
  // Optimize bundle analyzer
  webpack: (config, { isServer }) => {
    // Optimize for client-side performance
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
      };
    }
    
    return config;
  },
};

export default nextConfig;
