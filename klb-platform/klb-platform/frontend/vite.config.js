import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The Django API runs on port 8000 during development.
// Vite proxies API and media requests so the browser sees a single origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/media": "http://127.0.0.1:8000",
      "/sitemap.xml": "http://127.0.0.1:8000",
      "/robots.txt": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
