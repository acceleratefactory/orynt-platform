"use client"

import { useEffect, useState } from "react"

type Theme = "dark" | "light"

export function useTheme() {
    const [theme, setTheme] = useState<Theme>("dark")

    // On mount: read from localStorage, default to dark
    useEffect(() => {
        const saved = localStorage.getItem("orynt-theme") as Theme | null
        const initial: Theme = saved === "light" ? "light" : "dark"
        setTheme(initial)
        document.documentElement.setAttribute("data-theme", initial)
    }, [])

    const toggle = () => {
        const next: Theme = theme === "dark" ? "light" : "dark"
        setTheme(next)
        document.documentElement.setAttribute("data-theme", next)
        localStorage.setItem("orynt-theme", next)
    }

    return { theme, toggle }
}
