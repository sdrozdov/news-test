import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, proxy /api to the backend so the browser talks to a single origin
// (no CORS needed). In production set VITE_API_BASE_URL if the API is on a
// different host; leave it empty when the API is served from the same origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
