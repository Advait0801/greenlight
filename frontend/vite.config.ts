import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv, type ProxyOptions } from "vite";

// Ports and the API address come from environment variables (or the repository's .env), so two
// copies of the app can run side by side:
//   FRONTEND_PORT      dev server port (default 5173)
//   BACKEND_PORT       backend port, used for the default proxy target (default 8000)
//   API_PROXY_TARGET   where the dev server forwards /api (default http://localhost:$BACKEND_PORT)
//   VITE_API_BASE_URL  base URL the browser uses for API calls (default /api, i.e. through the proxy)

function port(value: string | undefined, fallback: number, name: string): number {
  if (value === undefined || value === "") return fallback;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 65535) {
    throw new Error(`${name} must be a port number between 1 and 65535, got "${value}"`);
  }
  return parsed;
}

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, "..", ""), ...process.env };
  const frontendPort = port(env.FRONTEND_PORT, 5173, "FRONTEND_PORT");
  const backendPort = port(env.BACKEND_PORT, 8000, "BACKEND_PORT");
  const target = env.API_PROXY_TARGET || `http://localhost:${backendPort}`;
  const proxy: Record<string, ProxyOptions> = {
    "/api": { target, changeOrigin: true, rewrite: (path) => path.replace(/^\/api/, "") },
  };

  return {
    plugins: [react(), tailwindcss()],
    envDir: "..",
    server: { port: frontendPort, strictPort: true, proxy },
    preview: { port: frontendPort, strictPort: true, proxy },
  };
});
