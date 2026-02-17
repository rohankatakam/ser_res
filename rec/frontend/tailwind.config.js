/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        serafis: {
          primary: '#6366f1',    // Indigo
          secondary: '#8b5cf6',  // Violet
          dark: '#0f172a',       // Slate 900
          surface: '#1e293b',    // Slate 800
          muted: '#64748b',      // Slate 500
          accent: '#22d3ee',     // Cyan
        }
      }
    },
  },
  plugins: [],
}
