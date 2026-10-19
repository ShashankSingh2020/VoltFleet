/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        fleet: {
          950: '#06090e',
          900: '#0b111a',
          850: '#101926',
          800: '#162234',
          700: '#23354d',
        }
      }
    },
  },
  plugins: [],
}