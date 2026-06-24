import tailwindcss from '@tailwindcss/vite'
import { TanStackRouterVite } from '@tanstack/router-plugin/vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { defineConfig, UserConfig } from 'vite'

const PORT = 57988

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const isLibMode = mode === 'lib'

  // Base configuration that applies to all environments
  const config: UserConfig = {
    plugins: [
      !isLibMode &&
        TanStackRouterVite({
          target: 'react',
          autoCodeSplitting: true,
          generatedRouteTree: 'src/route-tree.gen.ts',
        }),
      react(),
      tailwindcss(),
    ].filter(Boolean),
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5174,
      host: '100.112.29.96',
      proxy: {
        '/api': {
          target: `http://100.112.29.96:${PORT}`,
          changeOrigin: true,
        },
        '/socket.io': {
          target: `http://100.112.29.96:${PORT}`,
          ws: true,
          changeOrigin: true,
        },
      },
    },
  }

  // Library build configuration
  if (isLibMode) {
    config.build = {
      lib: {
        entry: path.resolve(__dirname, 'src/index.ts'),
        name: '@jaaz/agent-ui',
        fileName: (format: string) => `index.${format}.js`,
        formats: ['es'],
      },
      rollupOptions: {
        external: [
          'react',
          'react-dom',
          'react/jsx-runtime',
          '@tanstack/react-router',
          '@tanstack/react-query',
          'i18next',
          'react-i18next',
          'framer-motion',
          'motion',
          'lucide-react',
          'sonner',
          'zustand',
          'immer',
          'nanoid',
          'ahooks',
          'socket.io-client',
          'openai',
          'clsx',
          'tailwind-merge',
          'class-variance-authority',
          /@radix-ui\/.*/,
          /@tanstack\/.*/,
          /@excalidraw\/.*/,
          /@mdxeditor\/.*/,
        ],
        output: {
          globals: {
            react: 'React',
            'react-dom': 'ReactDOM',
            'react/jsx-runtime': 'react/jsx-runtime',
          },
        },
      },
    }
  }

  // Configure server based on environment
  if (mode === 'development') {
    config.server = config.server || {}
    config.server.proxy = {
      '/api': {
        target: `http://100.112.29.96:${PORT}`,
        changeOrigin: true,
      },
      '/socket.io': {
        target: `http://100.112.29.96:${PORT}`,
        ws: true,
        changeOrigin: true,
      },
    }
  }

  return config
})
