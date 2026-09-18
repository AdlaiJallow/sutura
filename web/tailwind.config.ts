import type { Config } from "tailwindcss";

// Sutura design tokens — "Ledger" direction: warm editorial-fintech.
// Colors are semantic first (on-track / overspent / saved / planned), decorative second.
const config: Config = {
  darkMode: ["class", ".dark"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["var(--font-fraunces)", "Georgia", "serif"],
        sans: ["var(--font-work-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-plex-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        paper: {
          DEFAULT: "#FAF6EF",
          raised: "#FFFFFF",
          sunken: "#F1EADD",
        },
        ink: {
          DEFAULT: "#241C14",
          soft: "#5B4E40",
          faint: "#8C7F6E",
        },
        rust: {
          50: "#FBEEE7",
          100: "#F3D6C4",
          300: "#E19A69",
          500: "#C1502E",
          600: "#A43F22",
          700: "#82311A",
        },
        // Semantic financial states — used everywhere a number needs a status color.
        ontrack: {
          DEFAULT: "#3F7A5E",
          bg: "#E7F1EA",
        },
        overspent: {
          DEFAULT: "#B3402C",
          bg: "#FBEAE6",
        },
        saved: {
          DEFAULT: "#B8862E",
          bg: "#F8EEDC",
        },
        planned: {
          DEFAULT: "#4A5B7A",
          bg: "#EAEEF5",
        },
        line: "#E4D9C6",
      },
      borderRadius: {
        sm: "4px",
        DEFAULT: "6px",
        md: "8px",
        lg: "12px",
        xl: "18px",
      },
      spacing: {
        18: "4.5rem",
        22: "5.5rem",
      },
      transitionTimingFunction: {
        ledger: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
      transitionDuration: {
        250: "250ms",
      },
      boxShadow: {
        card: "0 1px 2px rgba(36, 28, 20, 0.06), 0 1px 0 rgba(36, 28, 20, 0.04)",
        raised: "0 4px 16px rgba(36, 28, 20, 0.08)",
      },
      letterSpacing: {
        tightish: "-0.01em",
        wideish: "0.04em",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(2px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
      },
      animation: {
        "fade-in": "fade-in 250ms cubic-bezier(0.22, 1, 0.36, 1)",
        "pulse-soft": "pulse-soft 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
