/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0B0D14", // page background
          900: "#12141F", // panel surface
          800: "#191C2A", // raised surface / hover
          700: "#242838", // borders
          600: "#3A3F55", // muted borders / dividers
        },
        text: {
          primary: "#E8E9F0",
          muted: "#8D91A6",
          faint: "#5C6079",
        },
        signal: {
          allow: "#34D399",
          "allow-dim": "#0F2E24",
          sanitize: "#F2B84B",
          "sanitize-dim": "#332708",
          block: "#F0576A",
          "block-dim": "#341018",
        },
        accent: {
          DEFAULT: "#6E7BFF",
          dim: "#1B1D3A",
        },
      },
      fontFamily: {
        sans: ["Manrope", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.03) inset",
      },
    },
  },
  plugins: [],
};
