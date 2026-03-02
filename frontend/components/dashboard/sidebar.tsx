"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
    LayoutDashboard,
    Package,
    ShoppingCart,
    Users,
    BarChart3,
    Settings,
    HelpCircle,
    Megaphone,
    Tag,
    Store
} from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
    { name: "Overview", icon: LayoutDashboard, href: "/dashboard" },
    { name: "Products", icon: Package, href: "/dashboard/products" },
    { name: "Orders", icon: ShoppingCart, href: "/dashboard/orders", badge: "131" },
    { name: "Customers", icon: Users, href: "/dashboard/customers" },
    { name: "Marketing", icon: Megaphone, href: "/dashboard/marketing" },
    { name: "Analysis", icon: BarChart3, href: "/dashboard/analysis" },
]

const subItems = [
    { name: "Vendors", icon: Store, href: "/dashboard/vendors" },
    { name: "Settings", icon: Settings, href: "/dashboard/settings" },
    { name: "Help", icon: HelpCircle, href: "/dashboard/help" },
]

export function Sidebar() {
    const pathname = usePathname()

    return (
        <aside className="fixed left-0 top-0 h-screen w-64 bg-[#0F172A] text-slate-300 flex flex-col z-50">
            <div className="p-6 flex items-center gap-3">
                <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                    <svg
                        className="w-5 h-5 text-white"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M13 10V3L4 14h7v7l9-11h-7z"
                        />
                    </svg>
                </div>
                <span className="font-bold text-xl text-white tracking-tight">ORYNT</span>
            </div>

            <nav className="flex-1 px-4 mt-4 space-y-1">
                <p className="px-4 text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-4">
                    Main Menu
                </p>
                {navItems.map((item) => {
                    const isActive = pathname === item.href
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={cn(
                                "flex items-center justify-between px-4 py-2.5 rounded-xl transition-all duration-200 group",
                                isActive
                                    ? "bg-primary text-white premium-shadow"
                                    : "hover:bg-slate-800/50 hover:text-white"
                            )}
                        >
                            <div className="flex items-center gap-3">
                                <item.icon className={cn("w-5 h-5", isActive ? "text-white" : "text-slate-400 group-hover:text-white")} />
                                <span className="text-sm font-medium">{item.name}</span>
                            </div>
                            {item.badge && (
                                <span className={cn(
                                    "text-[10px] px-1.5 py-0.5 rounded-full font-bold",
                                    isActive ? "bg-white/20 text-white" : "bg-slate-800 text-slate-400"
                                )}>
                                    {item.badge}
                                </span>
                            )}
                        </Link>
                    )
                })}
            </nav>

            <div className="px-4 mb-8 space-y-1">
                <p className="px-4 text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-4">
                    Others
                </p>
                {subItems.map((item) => (
                    <Link
                        key={item.name}
                        href={item.href}
                        className="flex items-center gap-3 px-4 py-2.5 rounded-xl text-slate-400 hover:bg-slate-800/50 hover:text-white transition-all"
                    >
                        <item.icon className="w-5 h-5" />
                        <span className="text-sm font-medium">{item.name}</span>
                    </Link>
                ))}
            </div>

            <div className="p-4 mx-4 mb-6 rounded-2xl bg-slate-800/30 border border-slate-700/50">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-slate-700 overflow-hidden">
                        <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix" alt="User" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                        <p className="text-sm font-semibold text-white truncate">Jemma Grace</p>
                        <p className="text-xs text-slate-500 truncate">Admin</p>
                    </div>
                </div>
            </div>
        </aside>
    )
}
