import type { NextConfig } from "next";

const API_HOST = process.env.NEXT_PUBLIC_API_HOST || "http://localhost:8080";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,

  async rewrites(){
    return [
      // API requests > proxied to backend
      {
        source: "/api/:path*",
        destination: `${API_HOST}/api/:path*`,
      },
      // SRC redirect requests > proxied to backend
      {
        source: "/:short_code([a-zA-Z0-9]{7,9})",
        destination: `${API_HOST}/:short_code`,
      }
    ]
  }
};

export default nextConfig;
