import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // standalone bundles the minimal server for Railway/Docker deployments.
  // On Windows local dev, skip it (symlinks require elevated privileges).
  output: process.env.CI ? "standalone" : undefined,
  experimental: {
    typedRoutes: true,
  },
};

export default withNextIntl(nextConfig);
