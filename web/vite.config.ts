import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const apiUrl = process.env.DELPHI_CODE_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [tanstackRouter({ target: "react", autoCodeSplitting: true }), react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  build: {
    outDir: "../delphi_code/web",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": {
        target: apiUrl,
        changeOrigin: true,
        // The API refuses writes from other origins, so the proxy presents the API's own origin.
        configure: (proxy) => proxy.on("proxyReq", (request) => request.setHeader("origin", apiUrl)),
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts", "./src/test/apiServer.ts"],
  },
});
