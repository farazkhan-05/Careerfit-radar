/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#18212f',
        muted: '#687385',
        canvas: '#f6f8f1',
        paper: '#fffef9',
        mint: '#53d0a2',
        sky: '#67b7f7',
        coral: '#f97066',
        sun: '#f7c948',
        plum: '#8b5cf6',
        brand: {
          50: '#ecfbf5',
          100: '#d4f6e7',
          200: '#aeeccd',
          300: '#7ddfae',
          400: '#53d0a2',
          500: '#28b686',
          600: '#17936c',
          700: '#137558',
          800: '#145d49',
          900: '#124c3e',
        },
      },
      fontFamily: {
        display: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        playful: '0 18px 45px rgba(24, 33, 47, 0.08)',
        button: '4px 4px 0 rgba(24, 33, 47, 0.18)',
      },
    },
  },
  plugins: [],
}
