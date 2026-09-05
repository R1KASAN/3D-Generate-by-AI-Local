import nextConfig from "eslint-config-next/core-web-vitals";

const config = [
  ...nextConfig,
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "dist/**",
      "build/**",
      "test-results/**",
      "coverage/**",
      "**/*.min.js",
    ],
  },
];

export default config;
