"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/store/auth"
import { SetupFlow } from "@/components/onboarding/setup-flow"
import { OnboardingFlow } from "@/components/onboarding/onboarding-flow"
import { LogOut, Store, Tag, LayoutDashboard, Rocket } from "lucide-react"
import api from "@/lib/api"

interface Organization {
    id: string
    name: string
    owner_email: string
}

interface Brand {
    id: string
    name: string
    category: string
    organization_id: string
    seller_type: string | null
    payment_methods: string[]
    onboarding_completed: boolean
}

type DashboardState = "loading" | "no-org" | "no-brand" | "onboarding" | "ready" | "error"

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

            if (list.length === 0) { setState("no-brand"); return }

            const targetId = activeBrandId ?? list[0].id
            setActiveBrandId(targetId)
            const target = list.find((b) => b.id === targetId) ?? list[0]
            setActiveBrand(target)

            setState(!target.onboarding_completed ? "onboarding" : "ready")
        } catch (err: unknown) {
            const status = err && typeof err === "object" && "response" in err
                ? (err as { response: { status: number } }).response.status
                : undefined
            if (status === 404) {
                setState("no-org")
            } else {
                console.error("Dashboard load error:", err)
                setState("error")
            }
        }
    }

    useEffect(() => {
        if (activeBrandId && brands.length > 0) {
            const found = brands.find((b) => b.id === activeBrandId)
            if (found) {
                setActiveBrand(found)
                setState(!found.onboarding_completed ? "onboarding" : "ready")
            }
        }
    }, [activeBrandId])

    useEffect(() => { loadData() }, [])

    const handleLogout = async () => {
        await clearSession()
        router.push("/auth/login")
    }

    // ── Loading skeleton ──────────────────────────────────────────────────────
    if (state === "error") {
        return (
            <div className="flex flex-col items-center justify-center h-[calc(100vh-64px)] gap-4">
                <p className="text-lg font-bold font-display" style={{ color: "var(--color-text-primary)" }}>
                    Could not connect to the server
                </p>
                <p className="text-sm font-body" style={{ color: "var(--color-text-muted)" }}>
                    Make sure the backend is running, then try again.
                </p>
                <button
                    onClick={loadData}
                    className="mt-2 px-5 h-10 rounded-md text-sm font-semibold font-body transition-colors"
                    style={{ backgroundColor: "var(--color-accent)", color: "var(--color-text-inverse)" }}
                >
                    Retry
                </button>
            </div>
        )
    }

    if (state === "loading") {
        return (
            <div className="p-8 space-y-6">
                <div className="h-8 w-48 rounded-lg animate-pulse" style={{ backgroundColor: "var(--color-surface-raised)" }} />
                <div className="grid grid-cols-3 gap-4">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-36 rounded-lg animate-pulse" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }} />
                    ))}
                </div>
            </div>
        )
    }

    if (state === "no-org") return <div className="fixed inset-0 z-[100]" style={{ backgroundColor: "var(--color-bg)" }}><SetupFlow onComplete={loadData} /></div>
    if (state === "no-brand") return <div className="fixed inset-0 z-[100]" style={{ backgroundColor: "var(--color-bg)" }}><SetupFlow onComplete={loadData} skipToStep={2} /></div>
    if (state === "onboarding" && activeBrand) return (
        <div className="fixed inset-0 z-[100]" style={{ backgroundColor: "var(--color-bg)" }}>
            <OnboardingFlow brandId={activeBrand.id} brandName={activeBrand.name} onComplete={loadData} />
        </div>
    )

    return (
        <div className="p-8 space-y-8 max-w-[1400px]">

            {/* ── Page header ──────────────────────────────────────────────── */}
            <div className="flex items-start justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold font-display tracking-tight" style={{ color: "var(--color-text-primary)", letterSpacing: "-0.01em" }}>
                        Overview
                    </h1>
                    <p className="text-sm mt-1 font-body" style={{ color: "var(--color-text-muted)" }}>
                        Welcome back, {user?.email}
                    </p>
                </div>
                <button
                    onClick={handleLogout}
                    className="flex items-center gap-2 px-4 h-10 rounded-md text-sm font-medium font-body transition-colors duration-150"
                    style={{ color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}
                    onMouseEnter={e => {
                        e.currentTarget.style.backgroundColor = "var(--color-surface-raised)"
                        e.currentTarget.style.color = "var(--color-text-primary)"
                    }}
                    onMouseLeave={e => {
                        e.currentTarget.style.backgroundColor = "transparent"
                        e.currentTarget.style.color = "var(--color-text-muted)"
                    }}
                >
                    <LogOut className="w-4 h-4" strokeWidth={1.5} />
                    Log out
                </button>
            </div>

            {/* ── Metric cards row ──────────────────────────────────────────── */}
            <div className="grid gap-4 grid-cols-1 md:grid-cols-3">
                {/* Organization */}
                <div
                    className="rounded-lg p-6 flex items-start gap-4"
                    style={{
                        backgroundColor: "var(--color-surface)",
                        border: "1px solid var(--color-border)",
                        minHeight: "140px",
                    }}
                >
                    <div className="p-2.5 rounded-md flex-shrink-0" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                        <Store className="w-5 h-5" style={{ color: "var(--color-text-muted)" }} strokeWidth={1.5} />
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-[11px] font-semibold uppercase tracking-widest font-body mb-3" style={{ color: "var(--color-text-muted)", letterSpacing: "0.06em" }}>
                            Organization
                        </p>
                        <p className="text-2xl font-bold font-display truncate" style={{ color: "var(--color-text-primary)", letterSpacing: "-0.01em" }}>
                            {org?.name}
                        </p>
                        <p className="text-xs mt-1 truncate font-body" style={{ color: "var(--color-text-muted)" }}>
                            {org?.owner_email}
                        </p>
                    </div>
                </div>

                {/* Active Brand */}
                <div
                    className="rounded-lg p-6 flex items-start gap-4"
                    style={{
                        backgroundColor: "var(--color-surface)",
                        border: "1px solid var(--color-border)",
                        minHeight: "140px",
                    }}
                >
                    <div className="p-2.5 rounded-md flex-shrink-0" style={{ backgroundColor: "var(--color-accent-dim)" }}>
                        <Tag className="w-5 h-5" style={{ color: "var(--color-accent)" }} strokeWidth={1.5} />
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-[11px] font-semibold uppercase tracking-widest font-body mb-3" style={{ color: "var(--color-text-muted)", letterSpacing: "0.06em" }}>
                            Active Brand
                        </p>
                        <p className="text-2xl font-bold font-display truncate" style={{ color: "var(--color-text-primary)", letterSpacing: "-0.01em" }}>
                            {activeBrand?.name}
                        </p>
                        <p className="text-xs mt-1 font-body" style={{ color: "var(--color-text-muted)" }}>
                            {activeBrand?.category}
                            {activeBrand?.seller_type && (
                                <span
                                    className="ml-2 px-2 py-0.5 rounded-full text-[10px] font-semibold font-body capitalize"
                                    style={{ backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)" }}
                                >
                                    {activeBrand.seller_type.replace("_", " ")}
                                </span>
                            )}
                        </p>
                    </div>
                </div>

                {/* Brands count */}
                <div
                    className="rounded-lg p-6 flex items-start gap-4"
                    style={{
                        backgroundColor: "var(--color-surface)",
                        border: "1px solid var(--color-border)",
                        minHeight: "140px",
                    }}
                >
                    <div className="p-2.5 rounded-md flex-shrink-0" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                        <LayoutDashboard className="w-5 h-5" style={{ color: "var(--color-text-muted)" }} strokeWidth={1.5} />
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-[11px] font-semibold uppercase tracking-widest font-body mb-3" style={{ color: "var(--color-text-muted)", letterSpacing: "0.06em" }}>
                            Brands
                        </p>
                        <p className="text-4xl font-bold font-display" style={{ color: "var(--color-text-primary)", letterSpacing: "-0.02em", lineHeight: "1" }}>
                            {brands.length}
                        </p>
                        <p className="text-xs mt-2 font-body" style={{ color: "var(--color-text-muted)" }}>
                            registered brand{brands.length !== 1 ? "s" : ""}
                        </p>
                    </div>
                </div>
            </div>

            {/* ── Multi-brand list ────────────────────────────────────────── */}
            {brands.length > 1 && (
                <div
                    className="rounded-lg overflow-hidden"
                    style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}
                >
                    <div className="px-6 py-4" style={{ borderBottom: "1px solid var(--color-border)", backgroundColor: "var(--color-surface-raised)" }}>
                        <p className="text-[11px] font-semibold uppercase tracking-widest font-body" style={{ color: "var(--color-text-muted)", letterSpacing: "0.06em" }}>
                            All Brands
                        </p>
                    </div>
                    {brands.map((b, i) => (
                        <div
                            key={b.id}
                            className="flex items-center justify-between px-6 cursor-pointer transition-colors duration-100"
                            style={{
                                height: "52px",
                                borderBottom: i < brands.length - 1 ? "1px solid var(--color-border-subtle)" : "none",
                            }}
                            onClick={() => setActiveBrandId(b.id)}
                            onMouseEnter={e => (e.currentTarget.style.backgroundColor = "var(--color-surface-raised)")}
                            onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
                        >
                            <div>
                                <span className="text-sm font-medium font-body" style={{ color: "var(--color-text-primary)" }}>{b.name}</span>
                                <span className="text-xs ml-2 font-body" style={{ color: "var(--color-text-muted)" }}>{b.category}</span>
                            </div>
                            <span
                                className="text-[10px] font-semibold px-2.5 py-1 rounded-full font-body"
                                style={b.id === activeBrandId
                                    ? { backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)" }
                                    : { backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-muted)" }
                                }
                            >
                                {b.id === activeBrandId ? "Active" : "Switch"}
                            </span>
                        </div>
                    ))}
                </div>
            )}

            {/* ── Coming soon banner ──────────────────────────────────────── */}
            <div
                className="rounded-lg p-8 flex items-center gap-6"
                style={{
                    backgroundColor: "var(--color-surface)",
                    border: "1px solid var(--color-accent-border)",
                }}
            >
                <div
                    className="p-4 rounded-lg flex-shrink-0"
                    style={{ backgroundColor: "var(--color-accent-dim)" }}
                >
                    <Rocket className="w-6 h-6" style={{ color: "var(--color-accent)" }} strokeWidth={1.5} />
                </div>
                <div>
                    <h3 className="text-base font-bold font-display" style={{ color: "var(--color-accent)" }}>
                        {activeBrand?.name} is set up — connect your data sources next
                    </h3>
                    <p className="text-sm mt-1 font-body" style={{ color: "var(--color-text-muted)" }}>
                        Add your payment gateway, import your product catalog, and ORYNT will start scoring your SKUs automatically.
                    </p>
                </div>
            </div>
        </div>
    )
}
