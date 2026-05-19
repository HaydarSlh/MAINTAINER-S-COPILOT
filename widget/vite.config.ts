// Vite build config for the embeddable widget.
// Target: a SINGLE self-contained JS bundle (no code-splitting) so the loader
// can inject one file. Bundle size is a graded submission metric — keep deps
// minimal and review the gzipped size on every build.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // TODO: single-file output (inline assets), library mode, target esnext,
    //       report compressed size.
    rollupOptions: {},
  },
});
