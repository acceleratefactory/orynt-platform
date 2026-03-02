"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useAuthStore } from "@/store/auth"
import { BrandSwitcher } from "@/components/dashboard/brand-switcher"
import { LayoutDashboard } from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
    { name: "Overview", icon: LayoutDashboard, href: "/dashboard" },
]

export function Sidebar() {
    const pathname = usePathname()
    const { user } = useAuthStore()

    const email = user?.email ?? ""
    const initials = email.slice(0, 2).toUpperCase()

    return (
        <aside className="fixed left-0 top-0 h-screen w-64 bg-[#0F172A] text-slate-300 flex flex-col z-50">
            {/* Logo */}
            <div className="p-6 pb-4 flex items-center gap-3">
                <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center flex-shrink-0">
                    <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                </div>
                <span className="font-bold text-xl text-white tracking-tight">ORYNT</span>
            </div>

            {/* Brand Switcher — below logo */}
            <div className="pb-4">
                <BrandSwitcher />
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-4 space-y-1">
                {navItems.map((item) => {
                    const isActive = pathname === item.href
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-200",
                                isActive
                                    ? "bg-primary text-white"
                                    : "hover:bg-slate-800/50 hover:text-white text-slate-400"
                            )}
                        >
                            <item.icon className="w-5 h-5 flex-shrink-0" />
                            <span className="text-sm font-semibold">{item.name}</span>
                        </Link>
                    )
                })}
            </nav>

            {/* User profile */}
            <div className="p-4 mx-4 mb-6 rounded-2xl bg-slate-800/30 border border-slate-700/50">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-primary flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
                        {initials}
                    </div>
                    <div className="flex-1 overflow-hidden">
                        <p className="text-sm font-semibold text-white truncate">{email}</p>
                    </div>
                </div>
            </div>
        </aside>
    )
}
