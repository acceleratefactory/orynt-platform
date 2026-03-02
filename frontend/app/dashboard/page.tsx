"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/store/auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { SetupFlow } from "@/components/onboarding/setup-flow"
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

    const handleLogout = async () => {
        await clearSession()
        router.push("/auth/login")
    }

    if (state === "loading") {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-emerald-500" />
            </div>
        )
    }

    if (state === "no-org") {
        return <SetupFlow onComplete={loadData} />
    }

    if (state === "no-brand") {
        return <SetupFlow onComplete={loadData} skipToStep={2} />
    }

    // state === "ready" — show the placeholder dashboard
    const activeBrand = brands[0]

    return (
        <div className="min-h-screen bg-slate-950 text-white p-8">
            <div className="max-w-4xl mx-auto space-y-8">
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                        <p className="text-slate-400 mt-1 text-sm">{org?.name}</p>
                    </div>
                    <Button
                        variant="outline"
                        onClick={handleLogout}
                        className="border-slate-800 text-slate-400 hover:text-white hover:bg-slate-900"
                    >
                        Log out
                    </Button>
                </div>

                {/* Brand card */}
                <div className="grid gap-6 md:grid-cols-3">
                    <Card className="bg-slate-900 border-slate-800 text-white">
                        <CardHeader>
                            <CardTitle className="text-sm text-slate-400 uppercase tracking-widest">Active Brand</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p className="text-2xl font-bold">{activeBrand.name}</p>
                            <p className="text-slate-400 text-sm mt-1">{activeBrand.category}</p>
                        </CardContent>
                    </Card>

                    <Card className="bg-slate-900 border-slate-800 text-white">
                        <CardHeader>
                            <CardTitle className="text-sm text-slate-400 uppercase tracking-widest">Organization</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p className="text-2xl font-bold">{org?.name}</p>
                            <p className="text-slate-400 text-sm mt-1">{user?.email}</p>
                        </CardContent>
                    </Card>

                    <Card className="bg-slate-900 border-slate-800 text-white">
                        <CardHeader>
                            <CardTitle className="text-sm text-slate-400 uppercase tracking-widest">Brands</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p className="text-2xl font-bold">{brands.length}</p>
                            <p className="text-slate-400 text-sm mt-1">registered brand{brands.length !== 1 ? "s" : ""}</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Sprint 2 placeholder */}
                <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-lg p-8 text-center">
                    <h3 className="text-emerald-400 font-semibold text-lg mb-2">
                        🚀 {activeBrand.name} is set up!
                    </h3>
                    <p className="text-slate-400 text-sm">
                        Full analytics dashboard and AI-powered insights are coming in Sprint 2.
                    </p>
                </div>
            </div>
        </div>
    )
}
