"use client"

import { Sun, Moon } from "lucide-react"
import { useTheme } from "@/hooks/use-theme"

export function ThemeToggle() {
    const { theme, toggle } = useTheme()

    return (
        <button
            onClick={toggle}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            className="flex items-center justify-center w-10 h-10 rounded-full transition-colors duration-150"
            style={{
                border: "1px solid var(--color-border)",
                backgroundColor: "transparent",
                color: "var(--color-text-muted)",
            }}
            onMouseEnter={e => {
                e.currentTarget.style.backgroundColor = "var(--color-surface-raised)"
                e.currentTarget.style.borderColor = "var(--color-accent-border)"
                e.currentTarget.style.color = "var(--color-text-primary)"
            }}
            onMouseLeave={e => {
                e.currentTarget.style.backgroundColor = "transparent"
                e.currentTarget.style.borderColor = "var(--color-border)"
                e.currentTarget.style.color = "var(--color-text-muted)"
            }}
        >
            {theme === "dark"
                ? <Sun className="w-4 h-4" strokeWidth={1.5} />
                : <Moon className="w-4 h-4" strokeWidth={1.5} />
            }
        </button>
    )
}
