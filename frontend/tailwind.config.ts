import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // ORYNT brand tokens
        "orynt-bg":             "#0A0A0F",
        "orynt-surface":        "#111118",
        "orynt-surface-raised": "#17171F",
        "orynt-border":         "#1F1F2E",
        "orynt-border-subtle":  "#161622",
        "orynt-text":           "#F4F4F6",
        "orynt-text-secondary": "#9898AE",
        "orynt-text-muted":     "#5C5C73",
        "orynt-accent":         "#00C9A7",
        "orynt-accent-hover":   "#00B396",
        "orynt-scale":          "#22C55E",
        "orynt-monitor":        "#EAB308",
        "orynt-fix":            "#F97316",
        "orynt-kill":           "#EF4444",
        "orynt-chart-1":        "#00C9A7",
        "orynt-chart-2":        "#818CF8",
        "orynt-chart-3":        "#FB923C",
        "orynt-chart-4":        "#F472B6",
        // shadcn/ui compat tokens (kept for shadcn components)
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "Syne", "sans-serif"],
        body:    ["var(--font-body)", "DM Sans", "sans-serif"],
        mono:    ["var(--font-mono)", "JetBrains Mono", "monospace"],
        sans:    ["var(--font-body)", "DM Sans", "sans-serif"],
      },
      borderRadius: {
        sm:   "4px",
        md:   "8px",
        lg:   "12px",
        xl:   "16px",
        "2xl": "24px",
        full: "9999px",
      },
      boxShadow: {
        "orynt-sm":  "0 1px 2px rgba(0,0,0,0.4)",
        "orynt-md":  "0 2px 8px rgba(0,0,0,0.5)",
        "orynt-lg":  "0 4px 16px rgba(0,0,0,0.6)",
        "orynt-xl":  "0 8px 32px rgba(0,0,0,0.7)",
        "orynt-focus": "0 0 0 3px rgba(0,201,167,0.20)",
      },
    },
  },
  plugins: [],
};

export default config;
