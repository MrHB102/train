import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
  build: {
    target: 'es2022',
    chunkSizeWarningLimit: 2000,
    assetsInlineLimit: 0,
    rollupOptions: {
      // nomes estáveis (sem hash): facilita publicar como artefato e referenciar os arquivos
      output: { entryFileNames: 'assets/app.js', chunkFileNames: 'assets/[name].js', assetFileNames: 'assets/[name][extname]' },
    },
  },
  server: { host: true, port: 5173 },
});
