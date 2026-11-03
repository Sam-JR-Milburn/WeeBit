import type { NextConfig } from "next";
/*
const FRONTEND_HOST = process.env.NEXT_PUBLIC_FRONTEND_URL || "http://localhost:3080";
*/

let rawApiHost = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

// Ensure external URLs always have a protocol prefix
if (!rawApiHost.startsWith("http://") && !rawApiHost.startsWith("https://") && !rawApiHost.startsWith("/")) {
  rawApiHost = `https://${rawApiHost}`;
}

const API_HOST = rawApiHost;

const nextConfig: NextConfig = {
  reactCompiler: true,

  async rewrites(){
    return [
      {
        source: "/api/:path*",
        destination: `${API_HOST}/api/:path*`,
      },
      {
        source: "/:short_code([a-zA-Z0-9]{7,9})",
        destination: `${API_HOST}/:short_code`,
      }
    ];
  }
};

export default nextConfig;
