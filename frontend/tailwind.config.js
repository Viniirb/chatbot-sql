/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: 'rgb(var(--color-primary) / <alpha-value>)',
        'primary-hover': 'rgb(var(--color-primary-hover) / <alpha-value>)',
        'primary-dark': 'rgb(var(--color-primary-dark) / <alpha-value>)',
        'bubble-user': 'rgb(var(--color-bubble-user) / <alpha-value>)',
        accent: 'rgb(var(--color-accent) / <alpha-value>)',
        'gradient-start': 'rgb(var(--color-gradient-start) / <alpha-value>)',
        'gradient-end': 'rgb(var(--color-gradient-end) / <alpha-value>)',
        // Sobrescrever cores purple do Tailwind com as variáveis dinâmicas
        purple: {
          50: 'rgb(var(--color-primary) / 0.05)',
          100: 'rgb(var(--color-primary) / 0.1)',
          200: 'rgb(var(--color-primary) / 0.2)',
          300: 'rgb(var(--color-accent) / 0.7)',
          400: 'rgb(var(--color-accent) / 1)',
          500: 'rgb(var(--color-primary) / 1)',
          600: 'rgb(var(--color-primary-hover) / 1)',
          700: 'rgb(var(--color-primary-dark) / 1)',
          800: 'rgb(var(--color-primary-dark) / 0.8)',
          900: 'rgb(var(--color-primary-dark) / 0.6)',
        },
        // Adicionar também pink para os gradientes
        pink: {
          400: 'rgb(var(--color-gradient-end) / 0.8)',
          500: 'rgb(var(--color-gradient-end) / 1)',
          600: 'rgb(var(--color-gradient-end) / 0.7)',
        },
      },
      keyframes: {
        'slide-down': {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'pulse-slow': {
          '0%, 100%': { opacity: '0.3' },
          '50%': { opacity: '0.15' },
        },
        'gradient-shift': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'glow': {
          '0%, 100%': { opacity: '0.5', filter: 'blur(20px)' },
          '50%': { opacity: '0.8', filter: 'blur(30px)' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'blink': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
      },
      animation: {
        'slide-down': 'slide-down 0.3s ease-out',
        'pulse-slow': 'pulse-slow 8s ease-in-out infinite',
        'gradient-shift': 'gradient-shift 8s ease infinite',
        'float': 'float 3s ease-in-out infinite',
        'glow': 'glow 4s ease-in-out infinite',
        'shimmer': 'shimmer 3s linear infinite',
        'fade-in-up': 'fade-in-up 0.5s ease-out',
        'blink': 'blink 1s step-end infinite',
      },
      backgroundSize: {
        '200': '200% 200%',
      },
    },
  },
  plugins: [],
}