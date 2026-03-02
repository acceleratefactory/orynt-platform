"use client"

import { cn } from "@/lib/utils"

interface DashboardTabsProps {
    tabs: string[]
    activeTab: string
    onChange: (tab: string) => void
}

export function DashboardTabs({ tabs, activeTab, onChange }: DashboardTabsProps) {
    return (
        <div className="flex items-center gap-1 bg-slate-100 p-1.5 rounded-2xl w-fit">
            {tabs.map((tab) => {
                const isActive = activeTab === tab
                return (
                    <button
                        key={tab}
                        onClick={() => onChange(tab)}
                        className={cn(
                            "px-6 py-2 rounded-xl text-sm font-semibold transition-all duration-200",
                            isActive
                                ? "bg-white text-slate-900 premium-shadow"
                                : "text-slate-500 hover:text-slate-700 hover:bg-white/50"
                        )}
                    >
                        {tab}
                    </button>
                )
            })}
        </div>
    )
}
