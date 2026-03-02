"use client"

import { TrendingUp, TrendingDown, MoreVertical } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface MetricCardProps {
    title: string
    value: string
    change: number
    trend: "up" | "down"
    label?: string
    icon?: React.ReactNode
}

export function MetricCard({ title, value, change, trend, label, icon }: MetricCardProps) {
    const isUp = trend === "up"

    return (
        <Card className="premium-shadow border-none rounded-3xl group hover:scale-[1.02] transition-transform duration-300 overflow-hidden bg-white">
            <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                    <div className={cn(
                        "p-2.5 rounded-2xl",
                        isUp ? "bg-emerald-50 text-emerald-600" : "bg-purple-50 text-purple-600"
                    )}>
                        {icon}
                    </div>
                    <button className="text-slate-300 hover:text-slate-500">
                        <MoreVertical className="w-4 h-4" />
                    </button>
                </div>

                <div>
                    <p className="text-sm font-medium text-slate-500 mb-1">{title}</p>
                    <div className="flex items-baseline gap-2">
                        <h3 className="text-2xl font-bold text-slate-900">{value}</h3>
                    </div>

                    <div className="flex items-center gap-2 mt-4">
                        <div className={cn(
                            "flex items-center gap-0.5 text-xs font-bold px-2 py-0.5 rounded-full",
                            isUp ? "text-emerald-600 bg-emerald-50" : "text-amber-600 bg-amber-50"
                        )}>
                            {isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                            {change}%
                        </div>
                        <span className="text-xs text-slate-400 font-medium">vs previous period</span>
                    </div>
                </div>
            </div>

            {/* Decorative sparkline-like background element */}
            <div className="absolute bottom-0 right-0 left-0 h-1 bg-gradient-to-r from-transparent via-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        </Card>
    )
}
