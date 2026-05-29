import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { codecovVitePlugin } from '@codecov/vite-plugin'
import path from 'path'
import fs from 'fs'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    svelte(),
    // Codecov bundle analysis — after all other plugins (Vite + Svelte, not SvelteKit)
    codecovVitePlugin({
      enableBundleAnalysis: process.env.CODECOV_TOKEN !== undefined,
      bundleName: 'kairo-svelte-bundle',
      uploadToken: process.env.CODECOV_TOKEN,
    }),
  ],
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
    host: '127.0.0.1', // Force IPv4 to match Caddy reverse proxy
    configureServer(server) {
      // Post-middleware: runs after Vite's own handlers.
      // Serves public/404.html for any request that fell through unmatched.
      return () => {
        const notFoundPage = path.resolve(__dirname, 'public/404.html');
        server.middlewares.use((_req, res) => {
          if (fs.existsSync(notFoundPage)) {
            res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(fs.readFileSync(notFoundPage, 'utf-8'));
          } else {
            res.writeHead(404);
            res.end('404 Not Found');
          }
        });
      };
    },
  },
})

