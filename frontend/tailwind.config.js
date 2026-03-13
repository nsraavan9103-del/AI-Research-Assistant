/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: ['attribute', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        primary: {
          50:  'hsl(235 80% 97%)',
          100: 'hsl(235 75% 92%)',
          200: 'hsl(235 70% 82%)',
          300: 'hsl(235 65% 70%)',
          400: 'hsl(235 60% 58%)',
          500: 'hsl(235 55% 48%)',
          600: 'hsl(235 60% 40%)',
          700: 'hsl(235 65% 32%)',
          800: 'hsl(235 70% 24%)',
          900: 'hsl(235 75% 15%)',
        },
        surface: {
          light: '#ffffff',
          dark:  '#0f0f1a',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'thinking-dot': 'thinkingDot 1.4s infinite ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        thinkingDot: {
          '0%, 80%, 100%': { transform: 'scale(0)', opacity: '0' },
          '40%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
