"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useAuthStore } from "@/store/auth"
import { BrandSwitcher } from "@/components/dashboard/brand-switcher"
import {
    LayoutDashboard,
    Layers,
    Users,
    ShoppingBag,
    GitBranch,
    Megaphone,
    Zap,
    Mail,
    Plug,
    Settings,
} from "lucide-react"
import { cn } from "@/lib/utils"

// Definitive nav order from the brand identity document
const navItems = [
    { name: "Overview",          icon: LayoutDashboard, href: "/dashboard" },
    { name: "SKU Intelligence",  icon: Layers,          href: "/dashboard/sku" },
    { name: "Customers",         icon: Users,           href: "/dashboard/customers" },
    { name: "Orders",            icon: ShoppingBag,     href: "/dashboard/orders" },
    { name: "Channels",          icon: GitBranch,       href: "/dashboard/channels" },
    { name: "Ads & Influencers", icon: Megaphone,       href: "/dashboard/ads" },
    { name: "Automations",       icon: Zap,             href: "/dashboard/automations" },
    { name: "Weekly Digest",     icon: Mail,            href: "/dashboard/digest" },
]

const bottomNavItems = [
    { name: "Integrations", icon: Plug,     href: "/dashboard/integrations" },
    { name: "Settings",     icon: Settings, href: "/dashboard/settings" },
]

export function Sidebar() {
    const pathname = usePathname()
    const { user } = useAuthStore()

    const email = user?.email ?? ""
    const initials = email.slice(0, 2).toUpperCase()

    const NavLink = ({ item }: { item: typeof navItems[0] }) => {
        const isActive = pathname === item.href
        return (
            <Link
                href={item.href}
                className={cn(
                    "relative flex items-center gap-2.5 px-4 py-2.5 rounded-md transition-all duration-150 group",
                    isActive
                        ? "bg-[var(--color-accent-dim)] text-[var(--color-accent)]"
                        : "text-[var(--color-text-secondary)] hover:bg-white/[0.04] hover:text-[var(--color-text-primary)]"
                )}
            >
                {/* Active left border */}
                {isActive && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-[var(--color-accent)] rounded-r-full" />
                )}
                <item.icon
                    className={cn(
                        "w-4 h-4 flex-shrink-0 transition-colors",
                        isActive
                            ? "text-[var(--color-accent)]"
                            : "text-[var(--color-text-muted)] group-hover:text-[var(--color-text-secondary)]"
                    )}
                    strokeWidth={1.5}
                />
                <span className="text-sm font-medium font-body">{item.name}</span>
            </Link>
        )
    }

    return (
        <aside
            className="fixed left-0 top-0 h-screen w-60 flex flex-col z-50"
            style={{
                backgroundColor: "var(--color-surface)",
                borderRight: "1px solid var(--color-border)",
            }}
        >
            {/* ── Logo area — 64px ───────────────────────────────── */}
            <div className="h-16 flex items-center px-5 flex-shrink-0" style={{ borderBottom: "1px solid var(--color-border)" }}>
                <Link href="/dashboard" className="flex items-center gap-2.5">
                    {/* Compass mark — circle + arrow */}
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="12" cy="12" r="10" stroke="var(--color-accent)" strokeWidth="1.5" />
                        <line x1="8.5" y1="15.5" x2="15.5" y2="8.5" stroke="var(--color-accent)" strokeWidth="1.5" strokeLinecap="round" />
                        <polygon points="15.5,8.5 11.5,8.5 15.5,12.5" fill="var(--color-accent)" />
                    </svg>
                    {/* Wordmark — Syne font, all caps */}
                    <span
                        className="text-lg font-bold tracking-widest font-display"
                        style={{ color: "var(--color-text-primary)", letterSpacing: "0.12em" }}
                    >
                        ORYNT
                    </span>
                </Link>
            </div>

            {/* ── Brand Switcher ─────────────────────────────────── */}
            <div className="px-2 py-3 flex-shrink-0">
                <BrandSwitcher />
            </div>

            {/* ── Main Navigation ────────────────────────────────── */}
            <nav className="flex-1 overflow-y-auto px-2 space-y-0.5 pb-2">
                {navItems.map((item) => (
                    <NavLink key={item.name} item={item} />
                ))}

                {/* Divider */}
                <div className="my-3 mx-2" style={{ height: "1px", backgroundColor: "var(--color-border)" }} />

                {bottomNavItems.map((item) => (
                    <NavLink key={item.name} item={item} />
                ))}
            </nav>

            {/* ── User profile row — 64px ────────────────────────── */}
            <div
                className="h-16 flex items-center px-4 gap-3 flex-shrink-0"
                style={{ borderTop: "1px solid var(--color-border)" }}
            >
                <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                    style={{
                        backgroundColor: "var(--color-accent-dim)",
                        color: "var(--color-accent)",
                        border: "1px solid var(--color-accent-border)",
                    }}
                >
                    {initials}
                </div>
                <div className="flex-1 overflow-hidden">
                    <p
                        className="text-xs font-medium truncate font-body"
                        style={{ color: "var(--color-text-primary)" }}
                    >
                        {email}
                    </p>
                </div>
            </div>
        </aside>
    )
}
