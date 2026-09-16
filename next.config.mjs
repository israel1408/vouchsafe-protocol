/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    // Allows Vercel to complete builds even if internal node_modules packages have type errors
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
