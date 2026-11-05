import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxied (not CORS'd), as in the reference project. Set API_TARGET
      // when the backend isn't on localhost:8000 (e.g. in Docker).
      '/api': { target: process.env.API_TARGET ?? 'http://localhost:8000', changeOrigin: true },
    },
  },
});
