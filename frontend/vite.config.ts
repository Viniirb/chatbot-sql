import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom')) {
              return 'react-vendor';
            }
            if (id.includes('react-syntax-highlighter')) {
              return 'syntax-highlighter';
            }
            if (id.includes('highlight.js')) {
              return 'highlight-js';
            }
            if (id.includes('react-markdown')) {
              return 'markdown';
            }
            if (id.includes('framer-motion')) {
              return 'framer-motion';
            }
            if (id.includes('@headlessui')) {
              return 'headlessui';
            }
            if (id.includes('react-icons') || id.includes('lucide-react')) {
              return 'icons-vendor';
            }
            
            return 'vendor';
          }
        }
      }
    },
    chunkSizeWarningLimit: 1000,
  },
})