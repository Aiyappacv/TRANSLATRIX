import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "Aptos", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "#4F46E5",
          foreground: "#FFFFFF",
        },
        secondary: {
          DEFAULT: "#7C3AED",
          foreground: "#FFFFFF",
        },
        success: "#059669",
        warning: "#D97706",
        danger: "#DC2626",
        info: "#2563EB",
        navy: {
          950: "#020617",
          900: "#0F172A",
        },
        slate: {
          50: "#F8FAFC",
          100: "#F1F5F9",
          500: "#64748B",
          700: "#334155",
          900: "#0F172A",
        },
      },
      boxShadow: {
        enterprise: "0 16px 40px -30px rgba(15, 23, 42, 0.42)",
        card: "0 10px 30px -25px rgba(2, 6, 23, 0.45)",
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)",
        "mesh-finance": "radial-gradient(circle at 10% 20%, rgba(79,70,229,0.18), transparent 24%), radial-gradient(circle at 90% 0%, rgba(124,58,237,0.15), transparent 30%), linear-gradient(180deg, #F8FAFC 0%, #EEF2FF 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
