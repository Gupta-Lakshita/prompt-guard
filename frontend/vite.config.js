import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Prompt Guard frontend (Raima's part).
// Dev server runs on 5173 by default and talks to the FastAPI backend on :8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
