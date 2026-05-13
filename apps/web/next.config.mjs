import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // standalone bundles the minimal server for Railway/Docker deployments.
  // On Windows local dev, skip it (symlinks require elevated privileges).
  output: "standalone",
  experimental: {
    typedRoutes: true,
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "lh3.googleusercontent.com" },
      { protocol: "https", hostname: "*.googleusercontent.com" },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${BACKEND_URL}/api/v1/:path*`,
      },
    ];
  },
};

export default withNextIntl(nextConfig);
