/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',    // Optimized Docker builds
    images: {
        unoptimized: true,     // No image optimization server needed
    },
};

module.exports = nextConfig;
