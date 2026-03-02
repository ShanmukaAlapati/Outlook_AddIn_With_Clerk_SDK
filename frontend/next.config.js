/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          // ✅ Allow Outlook to embed in iframe
          { key: "X-Frame-Options", value: "ALLOWALL" },
          // ✅ Modern replacement for X-Frame-Options
          {
            key: "Content-Security-Policy",
            value: "frame-ancestors *;",
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
