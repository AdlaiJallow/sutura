import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output keeps the production Docker image small — only the
  // traced server bundle + minimal node_modules ship, not the full workspace.
  output: "standalone",
};

export default nextConfig;
