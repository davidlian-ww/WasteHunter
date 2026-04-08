/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        'walmart-blue': '#0053e2',
        'walmart-blue-hover': '#0046c7',
        'walmart-blue-pressed': '#0033a0',
        'walmart-spark': '#ffc220',
        'walmart-spark-hover': '#e6af1d',
        'walmart-red': '#ea1100',
        'walmart-green': '#2a8703',
        'walmart-warning': '#995213',
        'walmart-warning-bg': '#fff8e6',
        'walmart-gray': '#74767b',
        'walmart-gray-light': '#f5f5f5',
        'walmart-gray-border': '#d9d9d9',
      }
    }
  },
  plugins: [],
}
