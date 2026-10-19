import type { NextConfig } from "next";

// Hosted review copy (Docker on Render): one small Node server, and /api/* forwarded to the FastAPI process that runs
// beside it in the same container. Locally, the frontend calls http://localhost:8000 directly and /api is unused.
const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  cacheComponents: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_INTERNAL_URL}/:path*` }];
  },
  // The Cohorts page is the landing page (there is no Command centre any more).
  async redirects() {
    return [{ source: "/", destination: "/cohorts", permanent: false }];
  },
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
