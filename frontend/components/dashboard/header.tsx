"use client"

import { Search, Bell, ChevronDown } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

export function Header() {
    return (
        <header className="h-20 border-b border-slate-100 bg-white/80 backdrop-blur-md sticky top-0 z-40 px-8 flex items-center justify-between">
            <div className="flex items-center gap-4 flex-1">
                <h1 className="text-xl font-bold text-slate-900 mr-8">Overview</h1>
                <div className="relative max-w-md w-full hidden md:block">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                        placeholder="Search..."
                        className="pl-10 h-10 bg-slate-50 border-none rounded-full focus-visible:ring-primary/20"
                    />
                </div>
            </div>

            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" className="relative text-slate-600 rounded-full hover:bg-slate-50">
                    <Bell className="w-5 h-5" />
                    <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white" />
                </Button>
                <div className="h-10 w-px bg-slate-100 mx-2" />
                <Button variant="ghost" className="gap-2 text-slate-700 font-medium px-2 rounded-xl hover:bg-slate-50">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-xs">
                        KG
                    </div>
                    <span>Kemi's Boutique</span>
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                </Button>
            </div>
        </header>
    )
}
