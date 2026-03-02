"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/store/auth"
import { SetupFlow } from "@/components/onboarding/setup-flow"
import { MetricCard } from "@/components/dashboard/metric-card"
import { DashboardTabs } from "@/components/dashboard/tabs"
import {
    DollarSign,
    ShoppingCart,
    BarChart2,
    ArrowUpRight,
    TrendingUp,
    Package,
    Calendar
} from "lucide-react"
import api from "@/lib/api"

interface Organization {
    id: string
    name: string
    owner_email: string
    owner_phone: string | null
    created_at: string
}

interface Brand {
    id: string
    name: string
    category: string
    organization_id: string
}

type DashboardState = "loading" | "no-org" | "no-brand" | "ready"

export default function DashboardPage() {
    const { user, clearSession } = useAuthStore()
    const router = useRouter()
    const [state, setState] = useState<DashboardState>("loading")
    const [org, setOrg] = useState<Organization | null>(null)
    const [brands, setBrands] = useState<Brand[]>([])
    const [activeTab, setActiveTab] = useState("Insights")

    const loadData = async () => {
        try {
            const orgRes = await api.get("/api/organizations/me")
            setOrg(orgRes.data)

            const brandsRes = await api.get("/api/brands")
            setBrands(brandsRes.data)

            if (brandsRes.data.length === 0) {
                setState("no-brand")
            } else {
                setState("ready")
            }
        } catch (err: any) {
            if (err?.response?.status === 404) {
                setState("no-org")
            } else {
                console.error("Dashboard load error:", err)
                setState("no-org")
            }
        }
    }

    useEffect(() => {
        loadData()
    }, [])

    if (state === "loading") {
        return (
            <div className="flex h-[calc(100vh-80px)] items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-primary" />
            </div>
        )
    }

    if (state === "no-org") {
        return (
            <div className="fixed inset-0 z-[100] bg-slate-950">
                <SetupFlow onComplete={loadData} />
            </div>
        )
    }

    if (state === "no-brand") {
        return (
            <div className="fixed inset-0 z-[100] bg-slate-950">
                <SetupFlow onComplete={loadData} skipToStep={2} />
            </div>
        )
    }

    const activeBrand = brands[0]

    return (
        <div className="p-8 space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex flex-col gap-4">
                    <div className="flex items-center gap-2 text-slate-400 text-sm font-medium">
                        <Calendar className="w-4 h-4" />
                        <span>19 May - 24 Jul</span>
                    </div>
                    <DashboardTabs
                        tabs={["Insights", "Operations", "Assets"]}
                        activeTab={activeTab}
                        onChange={setActiveTab}
                    />
                </div>

                <div className="flex items-center gap-3">
                    <div className="text-right hidden sm:block">
                        <p className="text-sm font-bold text-slate-900">{activeBrand.name}</p>
                        <p className="text-xs font-semibold text-slate-500">{activeBrand.category}</p>
                    </div>
                    <button className="bg-primary text-white px-5 py-2.5 rounded-2xl font-bold text-sm hover:opacity-90 transition-opacity premium-shadow">
                        Create Campaign
                    </button>
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <MetricCard
                    title="Revenue"
                    value="$552,7K"
                    change={3}
                    trend="up"
                    icon={<DollarSign className="w-5 h-5" />}
                />
                <MetricCard
                    title="Total orders"
                    value="2,789K"
                    change={14}
                    trend="up"
                    icon={<ShoppingCart className="w-5 h-5" />}
                />
                <MetricCard
                    title="Gross profit"
                    value="$370,4K"
                    change={1.2}
                    trend="down"
                    icon={<BarChart2 className="w-5 h-5" />}
                />
                <MetricCard
                    title="Active customers"
                    value="64,4%"
                    change={3}
                    trend="up"
                    icon={<Users className="w-5 h-5" />}
                />
            </div>

            <div className="grid gap-6 md:grid-cols-3">
                {/* Large Chart Area Placeholder */}
                <div className="md:col-span-2 bg-white rounded-[32px] p-8 border border-slate-100 premium-shadow min-h-[400px]">
                    <div className="flex items-center justify-between mb-8">
                        <h3 className="font-bold text-lg text-slate-900">Income and expenses</h3>
                        <div className="flex items-center gap-4 text-xs font-bold">
                            <div className="flex items-center gap-1.5">
                                <div className="w-2 h-2 rounded-full bg-primary" />
                                <span className="text-slate-600">Income</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <div className="w-2 h-2 rounded-full bg-slate-300" />
                                <span className="text-slate-600">Expenses</span>
                            </div>
                        </div>
                    </div>
                    <div className="h-64 mt-12 flex items-end justify-between gap-2">
                        {[40, 60, 45, 90, 75, 85, 55].map((h, i) => (
                            <div key={i} className="flex-1 group relative">
                                <div
                                    className="bg-slate-50 rounded-2xl w-full transition-all duration-500 hover:bg-primary/10"
                                    style={{ height: `${h}%` }}
                                />
                                <div
                                    className="absolute bottom-0 left-1/4 right-1/4 bg-primary rounded-t-xl transition-all duration-500 opacity-80 group-hover:opacity-100"
                                    style={{ height: `${h * 0.7}%` }}
                                />
                            </div>
                        ))}
                    </div>
                    <div className="flex justify-between mt-4 text-[11px] font-bold text-slate-400 px-2 uppercase tracking-widest">
                        <span>May</span>
                        <span>Jun</span>
                        <span>Jul</span>
                        <span>Aug</span>
                        <span>Sep</span>
                        <span>Oct</span>
                        <span>Nov</span>
                    </div>
                </div>

                {/* Trending Sidebar */}
                <div className="space-y-6">
                    <div className="bg-white rounded-[32px] p-6 border border-slate-100 premium-shadow">
                        <h3 className="font-bold text-slate-900 mb-6 flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-emerald-500" />
                            Trending products
                        </h3>
                        <div className="space-y-4">
                            {[
                                { name: "Air conditioner Electrolux", price: "$24,338.7", color: "bg-primary/20", text: "text-primary" },
                                { name: "Smart watch Apple Watch", price: "$41,877.1", color: "bg-slate-900", text: "text-white" },
                                { name: "Air cooler Elboom Ocarina", price: "$25,433.2", color: "bg-primary/10", text: "text-primary" },
                            ].map((p) => (
                                <div key={p.name} className="flex flex-col gap-1 p-3 rounded-2xl hover:bg-slate-50 transition-colors cursor-pointer">
                                    <div className="flex items-center justify-between">
                                        <span className="text-sm font-bold text-slate-700 truncate mr-2">{p.name}</span>
                                        <span className={cn("text-[10px] font-black px-2 py-0.5 rounded-full", p.color, p.text)}>
                                            {p.price}
                                        </span>
                                    </div>
                                    <div className="h-1.5 w-full bg-slate-100 rounded-full mt-2 overflow-hidden">
                                        <div className="h-full bg-primary/40 w-2/3" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="bg-slate-900 rounded-[32px] p-6 premium-shadow text-white relative overflow-hidden">
                        <div className="relative z-10">
                            <div className="bg-white/10 w-fit p-2 rounded-xl mb-4">
                                <Package className="w-5 h-5 text-white" />
                            </div>
                            <h3 className="font-bold text-lg mb-2">Inventory Alerts</h3>
                            <p className="text-slate-400 text-xs mb-4">4 products are running low on stock. Check reports.</p>
                            <button className="text-xs font-bold underline decoration-primary underline-offset-4 hover:text-primary transition-colors">
                                View Assets →
                            </button>
                        </div>
                        <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-2xl" />
                    </div>
                </div>
            </div>
        </div>
    )
}
