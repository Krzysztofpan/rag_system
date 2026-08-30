import path from 'path'
import { defineConfig, loadEnv } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
function envValue(fileEnv: Record<string, string>, key: string): string {
    return process.env[key] ?? fileEnv[key] ?? ''
}

export default defineConfig(({ mode }) => {
    const root = path.resolve(__dirname, '..')
    // Load all keys from root .env in Node only; expose a whitelist via `define`.
    // process.env wins so Docker build-args work without copying .env into the image.
    const env = loadEnv(mode, root, '')

    return {
        plugins: [react(), tailwindcss()],
        envDir: root,
        define: {
            'import.meta.env.BACKEND_URL': JSON.stringify(envValue(env, 'BACKEND_URL') || '/api'),
            'import.meta.env.SUPABASE_URL': JSON.stringify(envValue(env, 'SUPABASE_URL')),
            'import.meta.env.SUPABASE_ANON_KEY': JSON.stringify(envValue(env, 'SUPABASE_ANON_KEY')),
        },
        resolve: {
            alias: {
                '@': path.resolve(__dirname, '.'),
            },
        },
        server: {
            proxy: {
                '/api': {
                    target: 'http://127.0.0.1:8000',
                    changeOrigin: true,
                    timeout: 0,
                    proxyTimeout: 0,
                },
            },
        },
    }
})
