/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#FFFFFF',
        secondary: '#F0F0F0',
        accent: '#0070F3',
        background: '#F5F5F5',
        text: '#000000',
      },
      fontFamily: {
        sans: ['sans-serif'],
      },
      fontSize: {
        'xs': '14px',
        'sm': '16px',
        'base': '18px',
        'lg': '20px',
        'xl': '24px',
      },
      fontWeight: {
        normal: 400,
        medium: 500,
        semibold: 600,
      },
    },
  },
  plugins: [],
}