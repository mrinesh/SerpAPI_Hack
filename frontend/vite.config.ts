import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// The dev server proxies /api to FastAPI, so the browser never needs CORS or the backend URL.
export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { "/api": loadEnv(mode, ".", "VITE_").VITE_BACKEND_URL ?? "http://localhost:8000" },
  },
}));
