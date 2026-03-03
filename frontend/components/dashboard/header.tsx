"use client"

import { Bell, Search } from "lucide-react"
import { useAuthStore } from "@/store/auth"
import { ThemeToggle } from "@/components/dashboard/theme-toggle"

export function Header() {
    const { user } = useAuthStore()
    const email = user?.email ?? ""
    const initials = email.slice(0, 2).toUpperCase()

    return (
        <header
            className="fixed top-0 left-60 right-0 h-16 z-40 flex items-center justify-between px-8 gap-4"
            style={{
                backgroundColor: "var(--color-bg)",
                borderBottom: "1px solid var(--color-border)",
            }}
        >
            {/* Search bar */}
            <div className="flex items-center gap-2.5 flex-1 max-w-sm">
                <div
                    className="flex items-center gap-2.5 w-full px-3 h-9 rounded-md transition-all"
                    style={{
                        backgroundColor: "var(--color-surface)",
                        border: "1px solid var(--color-border)",
                    }}
                >
                    <Search className="w-4 h-4 flex-shrink-0" style={{ color: "var(--color-text-muted)" }} strokeWidth={1.5} />
                    <input
                        type="text"
                        placeholder="Search..."
                        className="flex-1 text-sm bg-transparent border-none outline-none font-body"
                        style={{
                            color: "var(--color-text-primary)",
                            caretColor: "var(--color-accent)",
                        }}
                    />
                </div>
            </div>

            {/* Right: Notification bell + Avatar */}
            <div className="flex items-center gap-3">
                {/* Bell */}
                <button
                    className="w-9 h-9 rounded-md flex items-center justify-center transition-colors duration-150"
                    style={{ color: "var(--color-text-muted)" }}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = "var(--color-surface)")}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
                    aria-label="Notifications"
                >
                    <Bell className="w-4 h-4" strokeWidth={1.5} />
                </button>

                {/* Theme toggle */}
                <ThemeToggle />

                {/* Avatar */}
                <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold cursor-pointer flex-shrink-0 font-body"
                    style={{
                        backgroundColor: "var(--color-accent-dim)",
                        color: "var(--color-accent)",
                        border: "1px solid var(--color-accent-border)",
                    }}
                    title={email}
                >
                    {initials}
                </div>
            </div>
        </header>
    )
}
