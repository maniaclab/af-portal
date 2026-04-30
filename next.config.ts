import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",
  // undici is a transitive dep of Next.js; keep it external so webpack doesn't
  // try to bundle it (it uses native bindings that webpack can't resolve).
  serverExternalPackages: ["undici"],
};

export default config;
