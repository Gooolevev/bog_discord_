import type { NextConfig } from "next";
const staticSite = process.env.STATIC_SITE === "1";
const config: NextConfig = {
  ...(staticSite ? { output: "export", trailingSlash: true } : {}),
  basePath: process.env.NEXT_PUBLIC_BASE_PATH || "",
  poweredByHeader: false,
  images: {
    unoptimized: staticSite,
    remotePatterns: [{ protocol: "https", hostname: "cdn.discordapp.com" }],
  },
  headers: staticSite ? undefined : async () => {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            key: "Content-Security-Policy",
            value:
              "frame-src https://open.spotify.com; frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
          },
        ],
      },
    ];
  },
};
export default config;
