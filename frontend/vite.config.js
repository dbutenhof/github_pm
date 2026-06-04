// Generated-by: Cursor
// Assisted-by: Cursor
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

const DEFAULT_BACKEND_PORT = 8080;

function resolveBackendPort(env) {
  const raw = env.BACKEND_PORT;
  if (raw === undefined || raw === '') {
    return DEFAULT_BACKEND_PORT;
  }
  const port = Number.parseInt(raw, 10);
  if (!Number.isFinite(port) || port < 1 || port > 65535) {
    return DEFAULT_BACKEND_PORT;
  }
  return port;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendPort = resolveBackendPort(env);
  const backendTarget = `http://localhost:${backendPort}`;

  return {
    plugins: [react()],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
        },
      },
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/test/setup.js',
    },
  };
});
