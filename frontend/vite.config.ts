import path from 'path'
import { defineConfig, loadEnv } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
    const root = path.resolve(__dirname, '..')
    // Load all keys from root .env in Node only; expose a whitelist via `define`.
    const env = loadEnv(mode, root, '')

    return {
        plugins: [react(), tailwindcss()],
        envDir: root,
        define: {
            'import.meta.env.BACKEND_URL': JSON.stringify(env.BACKEND_URL ?? ''),
            'import.meta.env.SUPABASE_URL': JSON.stringify(env.SUPABASE_URL ?? ''),
            'import.meta.env.SUPABASE_ANON_KEY': JSON.stringify(env.SUPABASE_ANON_KEY ?? ''),
        },
        resolve: {
            alias: {
                '@': path.resolve(__dirname, '.'),
            },
        },
    }
})
