/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "system-ui", "sans-serif"],
        display: ["Outfit", "DM Sans", "system-ui", "sans-serif"],
      },
      colors: {
        ink: {
          950: "#0b0f17",
          900: "#111827",
          800: "#1f2937",
          700: "#374151",
          600: "#4b5563",
          500: "#6b7280",
          400: "#9ca3af",
        },
        brand: {
          50: "#f0fdfa",
          100: "#ccfbf1",
          200: "#99f6e4",
          300: "#5eead4",
          400: "#2dd4bf",
          500: "#14b8a6",
          600: "#0d9488",
          700: "#0f766e",
        },
        surface: {
          DEFAULT: "#faf9f7",
          card: "#ffffff",
          muted: "#f3f1ed",
        },
      },
      boxShadow: {
        soft: "0 2px 8px -2px rgba(15, 23, 42, 0.06), 0 8px 24px -8px rgba(15, 23, 42, 0.08)",
        lift: "0 4px 12px -2px rgba(15, 23, 42, 0.08), 0 12px 32px -12px rgba(13, 148, 136, 0.15)",
        glow: "0 0 0 1px rgba(20, 184, 166, 0.12), 0 8px 32px -8px rgba(13, 148, 136, 0.2)",
      },
      backgroundImage: {
        "mesh-page":
          "linear-gradient(180deg, #faf9f7 0%, #f5f3f0 100%), radial-gradient(ellipse 85% 55% at 50% -15%, rgba(20, 184, 166, 0.16), transparent 55%), radial-gradient(ellipse 55% 45% at 100% 5%, rgba(251, 191, 36, 0.1), transparent 50%), radial-gradient(ellipse 45% 40% at 0% 95%, rgba(99, 102, 241, 0.07), transparent 50%)",
      },
      animation: {
        "fade-in": "fadeIn 0.55s ease-out both",
        shimmer: "shimmer 1.2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%, 100%": { opacity: "0.45" },
          "50%": { opacity: "0.85" },
        },
      },
    },
  },
  plugins: [],
};
