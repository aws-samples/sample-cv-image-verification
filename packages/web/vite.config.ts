import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    // Define global to fix "global is not defined" error
    global: "window",
  },
  optimizeDeps: {
    exclude: ["ace-builds"],
    include: ["@aws-samples/cv-verification-api-client/src"],
    esbuildOptions: {
      // Node.js global to browser globalThis
      define: {
        global: "globalThis",
      },
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        global: resolve(__dirname, "src/global.js"),
      },
    },
    commonjsOptions: {
      exclude: [/node_modules\/ace-builds/],
    },
  },
  resolve: {
    alias: {
      // Handle file-loader syntax used by ace-builds
      "file-loader?esModule=false!./src-noconflict/snippets/":
        "./src-noconflict/snippets/",
    },
  },
});
