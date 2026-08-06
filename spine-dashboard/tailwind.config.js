/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          '"Inter"',
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      letterSpacing: {
        tight: "-0.025em",
        tighter: "-0.04em",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(0,0,0,0.24), 0 0 0 1px rgba(255,255,255,0.04)",
        panel: "0 8px 30px rgba(0,0,0,0.35), 0 0 0 1px rgba(255,255,255,0.05)",
        glow: "0 0 40px rgba(99, 102, 241, 0.12)",
      },
      colors: {
        spine: {
          bg: "#09090b",
          surface: "#111113",
          elevated: "#18181b",
          hover: "#1f1f23",
          line: "rgba(255,255,255,0.08)",
          "line-strong": "rgba(255,255,255,0.12)",
          border: "rgba(255,255,255,0.08)",
          "border-strong": "rgba(255,255,255,0.12)",
          fg: "#fafafa",
          muted: "#a1a1aa",
          subtle: "#71717a",
          accent: "#818cf8",
          "accent-strong": "#6366f1",
          "accent-muted": "rgba(99, 102, 241, 0.14)",
          success: "#34d399",
          warning: "#fbbf24",
          danger: "#f87171",
        },
      },
      borderColor: {
        DEFAULT: "rgba(255,255,255,0.08)",
        "spine-line": "rgba(255,255,255,0.08)",
        "spine-line-strong": "rgba(255,255,255,0.12)",
      },
      animation: {
        "fade-in": "fadeIn 0.35s ease-out",
        "slide-up": "slideUp 0.4s ease-out",
        "pulse-soft": "pulseSoft 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.45" },
        },
      },
    },
  },
  plugins: [],
};
