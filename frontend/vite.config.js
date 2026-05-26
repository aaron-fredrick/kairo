import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [svelte()],
  resolve: {
    alias: {
      '$lib': path.resolve(__dirname, './src/lib'),
    },
  },
  build: {
    outDir: path.resolve(__dirname, '../app/static'),
    emptyOutDir: true, // Clean the app/static folder before building
  },
  server: {
    host: '127.0.0.1' // Force IPv4 to match Caddy reverse proxy
  }
})
