import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In dev, /api is proxied to the FastAPI backend so the app never deals with
// CORS or absolute URLs. In Docker the target is the backend service.
// 127.0.0.1 rather than localhost: on Windows, localhost resolves to ::1
// first and uvicorn listens on IPv4 only.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
