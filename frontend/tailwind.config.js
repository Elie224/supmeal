/** @type {import("tailwindcss").Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        tomato: {
          50: "#FDE2DE",
          100: "#FBC8C0",
          300: "#F08C81",
          500: "#E94B3C",
          600: "#C8392E",
          700: "#A82C24",
        },
        cream: {
          50: "#FFF8F1",
          100: "#F6EBDC",
          200: "#EADDC6",
        },
        charcoal: {
          300: "#B5AFA3",
          500: "#7A7368",
          700: "#3F3A33",
          900: "#1F1B16",
        },
      },
      fontFamily: {
        display: ["Poppins", "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "6px",
        DEFAULT: "8px",
        md: "10px",
        lg: "12px",
        xl: "16px",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(31,27,22,0.06), 0 2px 8px rgba(31,27,22,0.04)",
        card: "0 4px 12px rgba(31,27,22,0.08)",
        elevated: "0 12px 32px rgba(31,27,22,0.12)",
      },
    },
  },
  plugins: [],
};