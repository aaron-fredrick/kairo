import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import path from 'path'
import fs from 'fs'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    svelte()
  ],

  resolve: {
    alias: {
      '$lib': path.resolve(__dirname, './src/lib'),
    },
  },

  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    minify: 'esbuild'
  },

  server: {
    host: '127.0.0.1',
    configureServer(server) {
      return () => {
        const notFoundPage = path.resolve(__dirname, 'public/404.html')

        server.middlewares.use((_req, res) => {
          if (fs.existsSync(notFoundPage)) {
            res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' })
            res.end(fs.readFileSync(notFoundPage, 'utf-8'))
          } else {
            res.writeHead(404)
            res.end('404 Not Found')
          }
        })
      }
    },
  },
})