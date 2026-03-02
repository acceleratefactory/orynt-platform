"use client"

import { Search, Bell, ChevronDown } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/store/auth"

export function Header() {
    const { user } = useAuthStore()

    const email = user?.email ?? ""
    const initials = email.slice(0, 2).toUpperCase()

    return (
        <header className="h-16 border-b border-slate-100 bg-white/80 backdrop-blur-md sticky top-0 z-40 px-8 flex items-center justify-between">
            <div className="flex items-center gap-4 flex-1">
                <div className="relative max-w-md w-full hidden md:block">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                        placeholder="Search..."
                        className="pl-10 h-10 bg-slate-50 border-none rounded-full focus-visible:ring-primary/20"
                    />
                </div>
            </div>

            <div className="flex items-center gap-3">
                <Button variant="ghost" size="icon" className="relative text-slate-600 rounded-full hover:bg-slate-50">
                    <Bell className="w-5 h-5" />
                </Button>
                <div className="h-8 w-px bg-slate-100" />
                <div className="flex items-center gap-2 px-2 py-1 rounded-xl hover:bg-slate-50 transition-colors cursor-default">
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white font-bold text-xs">
                        {initials}
                    </div>
                    <span className="text-sm font-semibold text-slate-700 hidden sm:block max-w-[160px] truncate">
                        {email}
                    </span>
                </div>
            </div>
        </header>
    )
}
