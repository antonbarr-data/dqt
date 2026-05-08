import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // output: "standalone" is enabled in CI/Linux builds only;
  // creating symlinks for standalone on Windows requires elevated privileges.
  experimental: {
    typedRoutes: true,
  },
};

export default withNextIntl(nextConfig);
