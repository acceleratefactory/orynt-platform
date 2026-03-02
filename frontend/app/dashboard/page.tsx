"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/store/auth"
import { SetupFlow } from "@/components/onboarding/setup-flow"
import { cn } from "@/lib/utils"
import {
    RocketIcon,
    StoreIcon,
    TagIcon,
    LayoutDashboardIcon,
    LogOut,
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
    const { user, clearSession, activeBrandId, setActiveBrandId } = useAuthStore()
    const router = useRouter()
    const [state, setState] = useState<DashboardState>("loading")
    const [org, setOrg] = useState<Organization | null>(null)
    const [brands, setBrands] = useState<Brand[]>([])
    const [activeBrand, setActiveBrand] = useState<Brand | null>(null)

    const loadData = async () => {
        try {
            const orgRes = await api.get("/api/organizations/me")
            setOrg(orgRes.data)

            const brandsRes = await api.get("/api/brands")
            const list: Brand[] = brandsRes.data
            setBrands(list)

            if (list.length === 0) {
                setState("no-brand")
                return
            }

            // Auto-select first brand; or stick with already-active brand
            const targetId = activeBrandId ?? list[0].id
            setActiveBrandId(targetId)
            setActiveBrand(list.find((b) => b.id === targetId) ?? list[0])
            setState("ready")
        } catch (err: any) {
            if (err?.response?.status === 404) {
                setState("no-org")
            } else {
                console.error("Dashboard load error:", err)
                setState("no-org")
            }
        }
    }

    // Re-fetch when activeBrandId changes (brand switch)
    useEffect(() => {
        if (activeBrandId && brands.length > 0) {
            const found = brands.find((b) => b.id === activeBrandId)
            if (found) setActiveBrand(found)
        }
    }, [activeBrandId])

    const handleLogout = async () => {
        await clearSession()
        router.push("/auth/login")
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
            <div className="fixed inset-0 z-[100] bg-white">
                <SetupFlow onComplete={loadData} />
            </div>
        )
    }

    if (state === "no-brand") {
        return (
            <div className="fixed inset-0 z-[100] bg-white">
                <SetupFlow onComplete={loadData} skipToStep={2} />
            </div>
        )
    }

    return (
        <div className="p-8 space-y-8">
            {/* Page heading */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-slate-900">Overview</h2>
                    <p className="text-slate-500 text-sm mt-1">Welcome back, {user?.email}</p>
                </div>
                <button
                    onClick={handleLogout}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition-all text-sm font-semibold w-fit"
                >
                    <LogOut className="w-4 h-4" />
                    Log out
                </button>
            </div>

            {/* Info cards — scoped to activeBrandId */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                <div className="bg-white rounded-[28px] p-7 border border-slate-100 premium-shadow flex items-start gap-5">
                    <div className="bg-primary/10 p-3 rounded-2xl">
                        <StoreIcon className="w-6 h-6 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-1">Organization</p>
                        <p className="text-xl font-bold text-slate-900 truncate">{org?.name}</p>
                        <p className="text-xs text-slate-400 mt-1 truncate">{org?.owner_email}</p>
                    </div>
                </div>

                <div className="bg-white rounded-[28px] p-7 border border-slate-100 premium-shadow flex items-start gap-5">
                    <div className="bg-violet-100 p-3 rounded-2xl">
                        <TagIcon className="w-6 h-6 text-violet-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-1">Active Brand</p>
                        <p className="text-xl font-bold text-slate-900 truncate">{activeBrand?.name}</p>
                        <p className="text-xs text-slate-400 mt-1">{activeBrand?.category}</p>
                    </div>
                </div>

                <div className="bg-white rounded-[28px] p-7 border border-slate-100 premium-shadow flex items-start gap-5">
                    <div className="bg-emerald-50 p-3 rounded-2xl">
                        <LayoutDashboardIcon className="w-6 h-6 text-emerald-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-1">Brands</p>
                        <p className="text-xl font-bold text-slate-900">{brands.length}</p>
                        <p className="text-xs text-slate-400 mt-1">registered brand{brands.length !== 1 ? "s" : ""}</p>
                    </div>
                </div>
            </div>

            {/* All brands list (only if more than one) */}
            {brands.length > 1 && (
                <div className="bg-white rounded-[28px] p-7 border border-slate-100 premium-shadow">
                    <h3 className="text-sm font-bold text-slate-900 mb-5 uppercase tracking-widest">All Brands</h3>
                    <div className="divide-y divide-slate-50">
                        {brands.map((b) => (
                            <div
                                key={b.id}
                                className={cn(
                                    "flex items-center justify-between py-4 cursor-pointer hover:bg-slate-50 px-2 rounded-xl transition-colors",
                                )}
                                onClick={() => setActiveBrandId(b.id)}
                            >
                                <div>
                                    <p className="font-bold text-slate-900 text-sm">{b.name}</p>
                                    <p className="text-xs text-slate-400 mt-0.5">{b.category}</p>
                                </div>
                                <span className={cn(
                                    "text-[10px] font-bold px-3 py-1 rounded-full",
                                    b.id === activeBrandId
                                        ? "bg-primary text-white"
                                        : "bg-slate-100 text-slate-500"
                                )}>
                                    {b.id === activeBrandId ? "Active" : "Switch"}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Sprint 2 coming-soon banner */}
            <div className={cn(
                "rounded-[28px] p-8 border border-primary/20 bg-primary/5 relative overflow-hidden"
            )}>
                <div className="absolute top-0 right-0 w-48 h-48 bg-primary/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl pointer-events-none" />
                <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center gap-6">
                    <div className="bg-primary p-4 rounded-3xl">
                        <RocketIcon className="w-8 h-8 text-white" />
                    </div>
                    <div className="flex-1">
                        <h3 className="text-lg font-bold text-primary">
                            🚀 {activeBrand?.name} is set up — Analytics coming in Sprint 2!
                        </h3>
                        <p className="text-slate-500 text-sm mt-1">
                            Your AI-powered sales insights, revenue charts, and product performance will appear right here.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
