"use client"

import { useState, useEffect } from "react"
import { CheckCircle2, AlertCircle, RefreshCw, ExternalLink, ArrowRight } from "lucide-react"
import { useAuthStore } from "@/store/auth"
import api from "@/lib/api"
import Link from "next/link"

// ── Types ─────────────────────────────────────────────────────────────────────

interface Integration {
    id: string
    type: string
    status: string          // 'connected' | 'error' | 'pending_customer_id'
    last_sync_at: string | null
    transaction_count: number
    created_at: string
}

// ── Static integration catalogue ─────────────────────────────────────────────

interface IntegrationMeta {
    type: string
    label: string
    description: string
    initial: string           // letter/abbrev for icon
    color: string             // hex accent color
    founderOnly?: boolean
}

const CATALOGUE: Record<string, IntegrationMeta[]> = {
    "Payment Gateways": [
        { type: "paystack", label: "Paystack", description: "Nigeria, Ghana, South Africa", initial: "P", color: "#00C9A7" },
        { type: "flutterwave", label: "Flutterwave", description: "Pan-African payment gateway", initial: "F", color: "#F5A623" },
        { type: "monnify", label: "Monnify", description: "Bank transfers & cards", initial: "M", color: "#046BF0" },
        { type: "opay", label: "OPay", description: "Mobile money & wallets", initial: "O", color: "#1DA462" },
    ],
    "E-Commerce": [
        { type: "shopify", label: "Shopify", description: "Online store orders & products", initial: "S", color: "#5C6AC4" },
        { type: "woocommerce", label: "WooCommerce", description: "WordPress e-commerce", initial: "W", color: "#7F54B3" },
        { type: "bumpa", label: "Bumpa CSV Import", description: "Manual CSV import from Bumpa", initial: "B", color: "#FF6B35" },
    ],
    "Digital Products": [
        { type: "selar", label: "Selar", description: "Nigeria's digital product marketplace", initial: "S", color: "#6C47FF" },
        { type: "gumroad", label: "Gumroad", description: "Global digital products platform", initial: "G", color: "#FF90E8" },
    ],
    "Open Banking": [
        { type: "mono", label: "Mono", description: "Bank account statements (NGN)", initial: "M", color: "#1652F0" },
    ],
    "Social Media": [
        { type: "social_media", label: "Instagram & Facebook Page", description: "Post reach, likes, page insights", initial: "IG", color: "#E1306C" },
        { type: "meta_ads", label: "Meta Ads", description: "Facebook & Instagram campaigns · ROAS", initial: "M", color: "#1877F2" },
        { type: "google_ads", label: "Google Ads", description: "Search & Display campaigns · ROAS", initial: "G", color: "#4285F4" },
    ],
    "Custom Platforms": [
        { type: "reseller_platform", label: "Reseller Platform", description: "Custom multi-storefront platform", initial: "R", color: "#F59E0B", founderOnly: true },
        { type: "preorder_platform", label: "Preorder Platform", description: "Pop-up campaign pre-order system", initial: "P", color: "#10B981", founderOnly: true },
    ],
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function timeAgo(iso: string | null): string {
    if (!iso) return "Never synced"
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
    if (diff < 60) return "Just now"
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return `${Math.floor(diff / 86400)}d ago`
}

function fmtDate(iso: string | null): string {
    if (!iso) return "—"
    return new Date(iso).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" })
}

function recordLabel(meta: IntegrationMeta, count: number): string {
    const ads = ["meta_ads", "google_ads"]
    const social = ["social_media"]
    if (ads.includes(meta.type)) return `${count.toLocaleString()} campaign days`
    if (social.includes(meta.type)) return `${count.toLocaleString()} metric rows`
    if (meta.type === "bumpa") return `${count.toLocaleString()} orders imported`
    return `${count.toLocaleString()} records`
}

// ── Status Badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string | undefined }) {
    if (status === "connected") {
        return (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold font-body"
                style={{ backgroundColor: "rgba(0,201,167,0.12)", color: "#00C9A7", border: "1px solid rgba(0,201,167,0.3)" }}>
                <CheckCircle2 className="w-3.5 h-3.5" /> Connected
            </span>
        )
    }
    if (status === "error") {
        return (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold font-body"
                style={{ backgroundColor: "rgba(239,68,68,0.1)", color: "#EF4444", border: "1px solid rgba(239,68,68,0.3)" }}>
                <AlertCircle className="w-3.5 h-3.5" /> Error
            </span>
        )
    }
    if (status === "pending_customer_id") {
        return (
            <span className="px-3 py-1 rounded-full text-xs font-semibold font-body"
                style={{ backgroundColor: "rgba(251,188,5,0.12)", color: "#FBBC05", border: "1px solid rgba(251,188,5,0.3)" }}>
                Setup needed
            </span>
        )
    }
    return (
        <span className="px-3 py-1 rounded-full text-xs font-semibold font-body"
            style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>
            Not connected
        </span>
    )
}

// ── Integration Card ──────────────────────────────────────────────────────────

function IntegrationCard({ meta, integration }: { meta: IntegrationMeta; integration: Integration | undefined }) {
    const status = integration?.status
    const connected = status === "connected"
    const isError = status === "error"

    return (
        <div className="rounded-2xl p-5 flex flex-col gap-4 transition-shadow"
            style={{
                backgroundColor: "var(--color-surface)",
                border: `1px solid ${isError ? "rgba(239,68,68,0.3)" : "var(--color-border)"}`,
                boxShadow: connected ? `0 0 0 1px ${meta.color}22` : undefined,
            }}>

            {/* Header row */}
            <div className="flex items-start gap-3">
                <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 text-sm font-bold font-display"
                    style={{
                        backgroundColor: connected ? `${meta.color}18` : "var(--color-surface-raised)",
                        color: connected ? meta.color : "var(--color-text-muted)",
                    }}>
                    {meta.initial}
                </div>
                <div className="flex-1 min-w-0">
                    <p className="font-bold text-sm font-display leading-tight" style={{ color: "var(--color-text-primary)" }}>
                        {meta.label}
                    </p>
                    <p className="text-xs font-body mt-0.5 truncate" style={{ color: "var(--color-text-muted)" }}>
                        {meta.description}
                    </p>
                </div>
                <StatusBadge status={status} />
            </div>

            {/* Stats when connected */}
            {connected && integration && (
                <div className="grid grid-cols-2 gap-2">
                    <div className="rounded-xl px-3 py-2.5" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Last synced</p>
                        <p className="text-xs font-semibold font-body mt-0.5" style={{ color: "var(--color-text-primary)" }}>
                            {timeAgo(integration.last_sync_at)}
                        </p>
                        <p className="text-[10px] font-body" style={{ color: "var(--color-text-muted)" }}>
                            {fmtDate(integration.last_sync_at)}
                        </p>
                    </div>
                    <div className="rounded-xl px-3 py-2.5" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Records</p>
                        <p className="text-xs font-semibold font-body mt-0.5" style={{ color: "var(--color-text-primary)" }}>
                            {recordLabel(meta, integration.transaction_count || 0)}
                        </p>
                    </div>
                </div>
            )}

            {/* Error banner */}
            {isError && (
                <div className="flex items-start gap-2 px-3 py-2 rounded-xl text-xs font-body"
                    style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.15)", color: "#EF4444" }}>
                    <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                    <span>Last sync failed. Reconnect to resume data pull.</span>
                </div>
            )}

            {/* CTA */}
            <div>
                <Link href="/dashboard/integrations"
                    className="inline-flex items-center gap-1.5 px-4 h-8 rounded-xl text-xs font-bold font-body transition-opacity hover:opacity-80"
                    style={connected || isError
                        ? { border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }
                        : { backgroundColor: meta.color, color: "#fff" }}>
                    {connected && <RefreshCw className="w-3 h-3" />}
                    {isError && <RefreshCw className="w-3 h-3" />}
                    {connected ? "Reconnect" : isError ? "Fix connection" : "Connect →"}
                </Link>
            </div>
        </div>
    )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SettingsIntegrationsPage() {
    const { activeBrandId, user } = useAuthStore()
    const [integrations, setIntegrations] = useState<Integration[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        if (!activeBrandId) return
        api.get(`/api/integrations?brand_id=${activeBrandId}`)
            .then(r => setIntegrations(r.data))
            .catch(() => setIntegrations([]))
            .finally(() => setLoading(false))
    }, [activeBrandId])

    const find = (type: string) => integrations.find(i => i.type === type)

    // Aggregate stats across all connected integrations
    const connected = integrations.filter(i => i.status === "connected")
    const totalRecords = connected.reduce((s, i) => s + (i.transaction_count || 0), 0)
    const connectedCount = connected.length
    const errorCount = integrations.filter(i => i.status === "error").length

    // Founder-only check: show custom platforms if user email is the owner
    // TODO: Replace with proper role check when role system is implemented
    const isFounder = true  // all users can see; hide by default once roles exist

    return (
        <div className="p-8 max-w-5xl space-y-10">

            {/* Page header */}
            <div className="flex items-end justify-between">
                <div>
                    <h1 className="text-2xl font-bold font-display" style={{ color: "var(--color-text-primary)" }}>
                        Integrations
                    </h1>
                    <p className="mt-1 text-sm font-body" style={{ color: "var(--color-text-muted)" }}>
                        Connect your sales channels, payment providers, and marketing tools
                    </p>
                </div>
                <Link href="/dashboard/integrations"
                    className="flex items-center gap-2 px-5 h-9 rounded-xl text-sm font-bold font-body"
                    style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                    Manage connections <ArrowRight className="w-4 h-4" />
                </Link>
            </div>

            {/* ── Data summary ── */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                    { label: "Connected", value: loading ? "—" : connectedCount.toString(), sub: "integrations" },
                    { label: "Errors", value: loading ? "—" : errorCount.toString(), sub: "need attention", danger: errorCount > 0 },
                    { label: "Total records", value: loading ? "—" : totalRecords.toLocaleString(), sub: "across all sources" },
                    { label: "Available", value: "15", sub: "integration types" },
                ].map(s => (
                    <div key={s.label} className="rounded-2xl p-5"
                        style={{
                            backgroundColor: "var(--color-surface)",
                            border: s.danger && !loading ? "1px solid rgba(239,68,68,0.3)" : "1px solid var(--color-border)",
                        }}>
                        <p className="text-xs font-body uppercase tracking-widest" style={{ color: "var(--color-text-muted)" }}>{s.label}</p>
                        <p className={`text-3xl font-bold font-display mt-2 ${s.danger && !loading ? "text-red-400" : ""}`}
                            style={s.danger && !loading ? { color: "#EF4444" } : { color: "var(--color-text-primary)" }}>
                            {s.value}
                        </p>
                        <p className="text-xs font-body mt-1" style={{ color: "var(--color-text-muted)" }}>{s.sub}</p>
                    </div>
                ))}
            </div>

            {/* ── Integration groups ── */}
            {loading ? (
                <div className="space-y-3">
                    {[1, 2, 3, 4, 5].map(i => (
                        <div key={i} className="h-20 rounded-2xl animate-pulse" style={{ backgroundColor: "var(--color-surface)" }} />
                    ))}
                </div>
            ) : (
                Object.entries(CATALOGUE).map(([group, items]) => {
                    // Skip if founder-only and not founder
                    const filtered = items.filter(i => !i.founderOnly || isFounder)
                    if (filtered.length === 0) return null
                    const groupConnected = filtered.filter(m => find(m.type)?.status === "connected").length

                    return (
                        <div key={group} className="space-y-3">
                            <div className="flex items-center gap-3">
                                <h2 className="text-xs font-bold uppercase tracking-widest font-body"
                                    style={{ color: "var(--color-text-muted)" }}>
                                    {group}
                                </h2>
                                <span className="text-xs font-body px-2 py-0.5 rounded-full"
                                    style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>
                                    {groupConnected}/{filtered.length} connected
                                </span>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {filtered.map(meta => (
                                    <IntegrationCard key={meta.type} meta={meta} integration={find(meta.type)} />
                                ))}
                            </div>
                        </div>
                    )
                })
            )}

            {/* ── Footer nudge ── */}
            {!loading && errorCount > 0 && (
                <div className="flex items-start gap-3 p-5 rounded-2xl"
                    style={{ backgroundColor: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)" }}>
                    <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "#EF4444" }} />
                    <div>
                        <p className="text-sm font-semibold font-body" style={{ color: "#EF4444" }}>
                            {errorCount} integration{errorCount > 1 ? "s" : ""} need attention
                        </p>
                        <p className="text-xs font-body mt-1" style={{ color: "var(--color-text-muted)" }}>
                            These integrations failed during the last sync and stopped pulling data.{" "}
                            <Link href="/dashboard/integrations" className="underline" style={{ color: "var(--color-accent)" }}>
                                Go to Integrations to reconnect →
                            </Link>
                        </p>
                    </div>
                </div>
            )}
        </div>
    )
}
