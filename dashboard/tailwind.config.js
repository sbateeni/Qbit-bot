/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0f172a", // slate-900
        card: "#1e293b", // slate-800
        textMain: "#f8fafc",
        textMuted: "#94a3b8",
        danger: "#ef4444",
        success: "#10b981"
      }
    },
  },
  plugins: [],
}
