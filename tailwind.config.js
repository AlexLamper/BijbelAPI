/** @type {import('tailwindcss').Config} */
module.exports = {
  // All marketing HTML lives under site/ (incl. partials). Rebuild with: npm run build:css
  content: ["./site/**/*.html", "./site/**/*.js"],
  theme: {
    extend: {},
  },
  plugins: [],
};
