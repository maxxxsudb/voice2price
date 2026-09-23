import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
    proxy: {
      '/api': {
        // Внутри Docker-контейнера localhost указывает на сам контейнер фронтенда,
        // поэтому по умолчанию проксируем на сервис backend по имени сети.
        // Локальная разработка (без Docker): VITE_BACKEND_URL=http://localhost:5000
        target: process.env.VITE_BACKEND_URL || 'http://backend:5000',
        changeOrigin: true,
      },
    },
    hmr: {
      port: 3000,
      protocol: 'ws',
    },
    watch: {
      usePolling: true,
    },
  },
});
