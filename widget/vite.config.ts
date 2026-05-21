import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    target: "esnext",
    // Single self-contained bundle — no code splitting.
    // The iframe loads one JS file; code splitting would require coordination.
    rollupOptions: {
      output: {
        manualChunks: undefined,
        entryFileNames: "assets/widget.[hash].js",
        chunkFileNames: "assets/widget.[hash].js",
        assetFileNames: "assets/widget.[hash][extname]",
        inlineDynamicImports: true,
      },
    },
    reportCompressedSize: true,
  },
});
