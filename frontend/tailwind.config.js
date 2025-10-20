/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        appia: {
          background: '#070B14',
          surface: '#0C111E',
          card: '#10172A',
          sunken: '#070A13',
          border: '#1C2437',
          divider: '#121B2D',
          muted: '#7D8AA8',
          foreground: '#E8ECF8',
          accent: '#4C8DFF',
          'accent-hover': '#5B9BFF',
          'accent-soft': '#1E2F4D',
          success: '#4ADE80',
          warning: '#FBBF24',
          danger: '#F87171',
          terminal: '#050912'
        }
      },
      fontFamily: {
        sans: ['"Inter"', 'ui-sans-serif', 'system-ui'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'ui-monospace', 'SFMono-Regular']
      },
      boxShadow: {
        'appia-card': '0 10px 40px rgba(8, 12, 24, 0.35)',
        'appia-glow': '0 0 0 1px rgba(76, 141, 255, 0.12), 0 20px 45px -15px rgba(76, 141, 255, 0.25)'
      }
    },
  },
  plugins: [],
};
