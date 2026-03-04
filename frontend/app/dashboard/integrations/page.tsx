"use client"

import { useState, useEffect, useRef } from "react"
import { CheckCircle2, AlertCircle, Plus, RefreshCw, Zap, Building2, ExternalLink, ShoppingBag, BarChart2 } from "lucide-react"
import { useAuthStore } from "@/store/auth"
import api from "@/lib/api"
import { useSearchParams } from "next/navigation"
import { Suspense } from "react"

interface Integration {
    id: string
    type: string
    status: string
    last_sync_at: string | null
    transaction_count: number
    created_at: string
}

// ── Gateway config ────────────────────────────────────────────────────────────

const PAYMENT_GATEWAYS = {
    paystack: {
        label: "Paystack",
        description: "Payment gateway — Nigeria, Ghana, South Africa",
        endpoint: "/api/integrations/paystack/connect",
        fields: [{ name: "secret_key", label: "Secret Key", placeholder: "sk_live_... or sk_test_...", type: "password" }],
        hint: "Paystack Dashboard → Settings → API Keys & Webhooks",
    },
    flutterwave: {
        label: "Flutterwave",
        description: "Payment gateway — Pan-African, 30+ currencies",
        endpoint: "/api/integrations/flutterwave/connect",
        fields: [{ name: "secret_key", label: "Secret Key", placeholder: "FLWSECK_TEST-... or FLWSECK-...", type: "password" }],
        hint: "Flutterwave Dashboard → Settings → API Keys",
    },
    monnify: {
        label: "Monnify (Moniepoint)",
        description: "Payment gateway — Nigeria bank transfers & cards",
        endpoint: "/api/integrations/monnify/connect",
        fields: [
            { name: "api_key", label: "API Key", placeholder: "MK_TEST_... or MK_PROD_...", type: "password" },
            { name: "secret_key", label: "Secret Key", placeholder: "Your Monnify secret key", type: "password" },
            { name: "contract_code", label: "Contract Code", placeholder: "e.g. 7984598283", type: "text" },
        ],
        hint: "Monnify Dashboard → Settings → API Keys",
    },
    opay: {
        label: "OPay",
        description: "Payment gateway — Nigeria, POS & online",
        endpoint: "/api/integrations/opay/connect",
        fields: [
            { name: "merchant_id", label: "Merchant ID", placeholder: "Your OPay Merchant ID", type: "text" },
            { name: "public_key", label: "Public Key", placeholder: "Your OPay public key", type: "password" },
            { name: "private_key", label: "Private Key", placeholder: "Your OPay private key", type: "password" },
        ],
        hint: "OPay Merchant Dashboard → Account Settings → API Keys",
    },
} as const

const ECOMMERCE_GATEWAYS = {
    woocommerce: {
        label: "WooCommerce",
        description: "E-Commerce — WordPress / WooCommerce stores",
        endpoint: "/api/integrations/woocommerce/connect",
        fields: [
            { name: "store_url", label: "Store URL", placeholder: "https://yourstore.com", type: "text" },
            { name: "consumer_key", label: "Consumer Key", placeholder: "ck_...", type: "password" },
            { name: "consumer_secret", label: "Consumer Secret", placeholder: "cs_...", type: "password" },
        ],
        hint: "WooCommerce Dashboard → Settings → Advanced → REST API → Add Key (Read/Write)",
    },
} as const

type GatewayKey = keyof typeof PAYMENT_GATEWAYS
type EcommerceKey = keyof typeof ECOMMERCE_GATEWAYS


// ── Connect Modal ─────────────────────────────────────────────────────────────

function ConnectModal({ gateway, onClose, onSuccess, brandId, config }: {
    gateway: GatewayKey | EcommerceKey; onClose: () => void; onSuccess: () => void; brandId: string;
    config?: { label: string; endpoint: string; fields: readonly { name: string; label: string; placeholder: string; type: string }[]; hint: string }
}) {
    const meta = config ?? PAYMENT_GATEWAYS[gateway as GatewayKey]
    const [values, setValues] = useState<Record<string, string>>({})
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")
    const [success, setSuccess] = useState(false)

    const handleConnect = async (e: React.FormEvent) => {
        e.preventDefault(); setLoading(true); setError("")
        try {
            await api.post(meta.endpoint, { ...values, brand_id: brandId })
            setSuccess(true)
            setTimeout(() => { onSuccess(); onClose() }, 1800)
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Failed to connect. Check your credentials and try again.")
        } finally { setLoading(false) }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ backgroundColor: "rgba(0,0,0,0.6)" }}>
            <div className="w-full max-w-md rounded-2xl p-6 space-y-5" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: "var(--color-accent-dim)" }}>
                        <Zap className="w-5 h-5" style={{ color: "var(--color-accent)" }} />
                    </div>
                    <div>
                        <h2 className="text-base font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Connect {meta.label}</h2>
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Encrypted and stored securely</p>
                    </div>
                </div>
                {success ? (
                    <div className="flex items-center gap-3 p-4 rounded-xl" style={{ backgroundColor: "var(--color-accent-dim)", border: "1px solid var(--color-accent-border)" }}>
                        <CheckCircle2 className="w-5 h-5 flex-shrink-0" style={{ color: "var(--color-accent)" }} />
                        <p className="text-sm font-semibold font-body" style={{ color: "var(--color-accent)" }}>Connected! Historical sync started.</p>
                    </div>
                ) : (
                    <form onSubmit={handleConnect} className="space-y-4">
                        {meta.fields.map(field => (
                            <div key={field.name} className="space-y-1.5">
                                <label className="block text-xs font-semibold font-body" style={{ color: "var(--color-text-secondary)" }}>{field.label}</label>
                                <input type={field.type} placeholder={field.placeholder} value={values[field.name] ?? ""}
                                    onChange={e => setValues(v => ({ ...v, [field.name]: e.target.value }))} required
                                    className="w-full h-11 px-4 rounded-xl text-sm font-mono outline-none"
                                    style={{ backgroundColor: "var(--color-surface-raised)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" }}
                                    onFocus={e => e.currentTarget.style.boxShadow = "0 0 0 2px var(--color-accent-border)"}
                                    onBlur={e => e.currentTarget.style.boxShadow = "none"} />
                            </div>
                        ))}
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>{meta.hint}</p>
                        {error && (
                            <div className="flex items-start gap-2 p-3 rounded-xl text-xs font-body"
                                style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#EF4444" }}>
                                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />{error}
                            </div>
                        )}
                        <div className="flex gap-3 pt-1">
                            <button type="button" onClick={onClose} className="flex-1 h-11 rounded-xl text-sm font-semibold font-body"
                                style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>Cancel</button>
                            <button type="submit" disabled={loading} className="flex-1 h-11 rounded-xl text-sm font-bold font-body disabled:opacity-60"
                                style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                                {loading ? "Connecting..." : `Connect ${meta.label}`}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    )
}

// ── Shopify Card ──────────────────────────────────────────────────────────────

function ShopifyCard({ integration, brandId, onSuccess }: {
    integration: Integration | undefined; brandId: string; onSuccess: () => void
}) {
    const connected = integration?.status === "connected"
    const [shopInput, setShopInput] = useState("")
    const [showInput, setShowInput] = useState(false)
    const [error, setError] = useState("")
    const fmt = (iso: string | null) => iso
        ? new Date(iso).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" }) : "Never"

    const handleConnect = () => {
        let shop = shopInput.trim()
        if (!shop) { setError("Enter your Shopify store URL"); return }
        if (!shop.includes(".myshopify.com")) shop = `${shop}.myshopify.com`
        // Redirect to backend OAuth initiation
        window.location.href = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/integrations/shopify/auth?shop=${encodeURIComponent(shop)}&brand_id=${brandId}`
    }

    return (
        <div className="rounded-2xl p-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center"
                        style={{ backgroundColor: connected ? "rgba(0,201,167,0.1)" : "var(--color-surface-raised)" }}>
                        <ShoppingBag className="w-6 h-6" style={{ color: connected ? "var(--color-accent)" : "var(--color-text-muted)" }} />
                    </div>
                    <div>
                        <h3 className="font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Shopify</h3>
                        <p className="text-sm font-body" style={{ color: "var(--color-text-muted)" }}>
                            E-Commerce — full sync: products, customers, orders
                        </p>
                    </div>
                </div>
                {connected ? (
                    <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold font-body"
                        style={{ backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)", border: "1px solid var(--color-accent-border)" }}>
                        <CheckCircle2 className="w-3.5 h-3.5" /> Connected
                    </span>
                ) : (
                    <span className="px-3 py-1 rounded-full text-xs font-semibold font-body"
                        style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>
                        Not connected
                    </span>
                )}
            </div>

            {connected && (
                <div className="mt-5 grid grid-cols-3 gap-4">
                    {[
                        { label: "Last synced", value: fmt(integration!.last_sync_at) },
                        { label: "Orders synced", value: integration!.transaction_count.toLocaleString() },
                        { label: "Webhooks", value: "Active" },
                    ].map(s => (
                        <div key={s.label} className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                            <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>{s.label}</p>
                            <p className="mt-1 text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>{s.value}</p>
                        </div>
                    ))}
                </div>
            )}

            {showInput && !connected && (
                <div className="mt-4 space-y-3">
                    <div className="flex gap-2">
                        <div className="flex-1 relative">
                            <input type="text" placeholder="your-store.myshopify.com"
                                value={shopInput} onChange={e => { setShopInput(e.target.value); setError("") }}
                                onKeyDown={e => e.key === "Enter" && handleConnect()}
                                className="w-full h-11 px-4 rounded-xl text-sm font-mono outline-none"
                                style={{ backgroundColor: "var(--color-surface-raised)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" }}
                                onFocus={e => e.currentTarget.style.boxShadow = "0 0 0 2px var(--color-accent-border)"}
                                onBlur={e => e.currentTarget.style.boxShadow = "none"} />
                        </div>
                        <button onClick={handleConnect}
                            className="px-5 h-11 rounded-xl text-sm font-bold font-body"
                            style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                            Authorize →
                        </button>
                    </div>
                    {error && <p className="text-xs font-body" style={{ color: "#EF4444" }}>{error}</p>}
                    <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>
                        You'll be redirected to Shopify to grant access. No secret keys needed.
                    </p>
                </div>
            )}

            <div className="mt-5 flex items-center gap-3">
                {connected ? (
                    <button onClick={() => setShowInput(true)} className="flex items-center gap-2 px-4 h-9 rounded-xl text-sm font-semibold font-body"
                        style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>
                        <RefreshCw className="w-3.5 h-3.5" /> Re-connect Store
                    </button>
                ) : !showInput ? (
                    <button onClick={() => setShowInput(true)} className="flex items-center gap-2 px-5 h-9 rounded-xl text-sm font-bold font-body"
                        style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                        <Plus className="w-4 h-4" /> Connect Shopify
                    </button>
                ) : (
                    <button onClick={() => { setShowInput(false); setError("") }} className="text-sm font-semibold font-body"
                        style={{ color: "var(--color-text-muted)" }}>
                        Cancel
                    </button>
                )}
            </div>
        </div>
    )
}

// ── Mono Card ─────────────────────────────────────────────────────────────────

function MonoBankCard({ integration, brandId, onSuccess }: {
    integration: Integration | undefined; brandId: string; onSuccess: () => void
}) {
    const connected = integration?.status === "connected"
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")
    const [pendingCount, setPendingCount] = useState<number | null>(null)
    const fmt = (iso: string | null) => iso
        ? new Date(iso).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" }) : "Never"

    useEffect(() => {
        if (!connected || !brandId) return
        api.get(`/api/orders/inbox?brand_id=${brandId}&page_size=1`).then(r => setPendingCount(r.data.total)).catch(() => { })
    }, [connected, brandId])

    const handleConnect = async () => {
        setLoading(true); setError("")
        try {
            const res = await api.post("/api/integrations/mono/initiate", { brand_id: brandId })
            const monoUrl = res.data.mono_url
            if (!monoUrl) { setError("Could not get Mono Connect URL. Ensure MONO_SECRET_KEY is set."); setLoading(false); return }
            const popup = window.open(monoUrl, "mono_connect", "width=500,height=700,top=100,left=200,scrollbars=yes")
            const handler = async (event: MessageEvent) => {
                if (event.data?.type === "mono.connect.widget.account_linked" || event.data?.type === "mono.events.account_linked") {
                    const code = event.data?.data?.code
                    popup?.close()
                    window.removeEventListener("message", handler)
                    if (code) {
                        try { await api.post("/api/integrations/mono/exchange", { code, brand_id: brandId }); onSuccess() }
                        catch (err: any) { setError(err?.response?.data?.detail || "Failed to link bank account.") }
                    }
                    setLoading(false)
                }
            }
            window.addEventListener("message", handler)
            const checkClosed = setInterval(() => { if (popup?.closed) { clearInterval(checkClosed); window.removeEventListener("message", handler); setLoading(false) } }, 1000)
        } catch (err: any) { setError(err?.response?.data?.detail || "Failed to initiate Mono Connect."); setLoading(false) }
    }

    return (
        <div className="rounded-2xl p-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ backgroundColor: connected ? "rgba(0,201,167,0.1)" : "var(--color-surface-raised)" }}>
                        <Building2 className="w-6 h-6" style={{ color: connected ? "var(--color-accent)" : "var(--color-text-muted)" }} />
                    </div>
                    <div>
                        <h3 className="font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Bank Account (Mono)</h3>
                        <p className="text-sm font-body" style={{ color: "var(--color-text-muted)" }}>Import bank transfers → Order Inbox for review</p>
                    </div>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-semibold font-body flex items-center gap-1.5`}
                    style={connected ? { backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)", border: "1px solid var(--color-accent-border)" } : { backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>
                    {connected && <CheckCircle2 className="w-3.5 h-3.5" />} {connected ? "Connected" : "Not connected"}
                </span>
            </div>
            {connected && (
                <div className="mt-5 grid grid-cols-2 gap-4">
                    <div className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Last synced</p>
                        <p className="mt-1 text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>{fmt(integration!.last_sync_at)}</p>
                    </div>
                    <div className="rounded-xl p-4 cursor-pointer" style={{ backgroundColor: pendingCount ? "rgba(245,158,11,0.1)" : "var(--color-surface-raised)", border: pendingCount ? "1px solid rgba(245,158,11,0.3)" : "none" }}
                        onClick={() => pendingCount && (window.location.href = "/dashboard/orders/inbox")}>
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Unmatched transfers</p>
                        <p className="mt-1 text-sm font-semibold font-body" style={{ color: pendingCount ? "#F59E0B" : "var(--color-text-primary)" }}>{pendingCount ?? "—"}{pendingCount ? " → Review" : ""}</p>
                    </div>
                </div>
            )}
            {error && <div className="mt-4 text-xs font-body p-3 rounded-xl" style={{ backgroundColor: "rgba(239,68,68,0.08)", color: "#EF4444" }}>{error}</div>}
            <div className="mt-5 flex items-center gap-3">
                <button onClick={handleConnect} disabled={loading} className="flex items-center gap-2 px-5 h-9 rounded-xl text-sm font-bold font-body disabled:opacity-60"
                    style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                    {loading ? "Opening..." : connected ? <><RefreshCw className="w-3.5 h-3.5" /> Re-connect</> : <><Plus className="w-4 h-4" /> Connect Bank Account</>}
                </button>
                {connected && <a href="/dashboard/orders/inbox" className="text-sm font-semibold font-body flex items-center gap-1.5" style={{ color: "var(--color-accent)" }}><ExternalLink className="w-4 h-4" /> Order Inbox</a>}
            </div>
        </div>
    )
}

// ── Gateway Card ──────────────────────────────────────────────────────────────

function GatewayCard({ gatewayKey, integration, onConnect, config }: {
    gatewayKey: GatewayKey | EcommerceKey; integration: Integration | undefined; onConnect: () => void;
    config?: { label: string; description: string }
}) {
    const meta = config ?? PAYMENT_GATEWAYS[gatewayKey as GatewayKey]
    const connected = integration?.status === "connected"
    const fmt = (iso: string | null) => iso ? new Date(iso).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" }) : "Never"
    return (
        <div className="rounded-2xl p-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold"
                        style={{ backgroundColor: connected ? "rgba(0,201,167,0.1)" : "var(--color-surface-raised)", color: connected ? "var(--color-accent)" : "var(--color-text-muted)" }}>
                        {meta.label[0]}
                    </div>
                    <div>
                        <h3 className="font-bold font-display" style={{ color: "var(--color-text-primary)" }}>{meta.label}</h3>
                        <p className="text-sm font-body" style={{ color: "var(--color-text-muted)" }}>{meta.description}</p>
                    </div>
                </div>
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold font-body"
                    style={connected ? { backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)", border: "1px solid var(--color-accent-border)" } : { backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>
                    {connected && <CheckCircle2 className="w-3.5 h-3.5" />} {connected ? "Connected" : "Not connected"}
                </span>
            </div>
            {connected && (
                <div className="mt-5 grid grid-cols-2 gap-4">
                    {[{ label: "Last synced", value: fmt(integration!.last_sync_at) }, { label: "Orders imported", value: integration!.transaction_count.toLocaleString() }].map(s => (
                        <div key={s.label} className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                            <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>{s.label}</p>
                            <p className="mt-1 text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>{s.value}</p>
                        </div>
                    ))}
                </div>
            )}
            <div className="mt-5">
                {connected ? (
                    <button onClick={onConnect} className="flex items-center gap-2 px-4 h-9 rounded-xl text-sm font-semibold font-body"
                        style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>
                        <RefreshCw className="w-3.5 h-3.5" /> Re-connect / Update Key
                    </button>
                ) : (
                    <button onClick={onConnect} className="flex items-center gap-2 px-5 h-9 rounded-xl text-sm font-bold font-body"
                        style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                        <Plus className="w-4 h-4" /> Connect {meta.label}
                    </button>
                )}
            </div>
        </div>
    )
}

// ── Reseller Platform Card ────────────────────────────────────────────────────

function ResellerPlatformCard({ integration, brandId, onSuccess }: {
    integration: Integration | undefined; brandId: string; onSuccess: () => void
}) {
    const status = integration?.status
    const connected = status === "connected" || status === "syncing"
    const pending = status === "pending_confirmation"
    const fmt = (iso: string | null) => iso
        ? new Date(iso).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" }) : "Never"

    const [step, setStep] = useState<"idle" | "form" | "preview" | "syncing">(
        connected ? "idle" : pending ? "preview" : "idle"
    )
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")
    const [preview, setPreview] = useState<{ storefronts_found: number; integration_id: string; preview: any[] } | null>(null)
    const [fields, setFields] = useState({
        db_host: "", db_name: "", db_user: "", db_password: "", db_prefix: "wp_"
    })

    const handleConnect = async (e: React.FormEvent) => {
        e.preventDefault(); setLoading(true); setError("")
        try {
            const res = await api.post("/api/integrations/reseller-platform/connect", {
                ...fields, brand_id: brandId
            })
            setPreview(res.data)
            setStep("preview")
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Connection failed. Check your database credentials.")
        } finally { setLoading(false) }
    }

    const handleConfirm = async () => {
        if (!preview) return
        setLoading(true); setError("")
        try {
            await api.post("/api/integrations/reseller-platform/confirm", {
                integration_id: preview.integration_id, brand_id: brandId
            })
            setStep("syncing")
            onSuccess()
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Confirmation failed.")
        } finally { setLoading(false) }
    }

    return (
        <div className="rounded-2xl p-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold font-mono"
                        style={{ backgroundColor: connected ? "rgba(0,201,167,0.1)" : "var(--color-surface-raised)", color: connected ? "var(--color-accent)" : "var(--color-text-muted)" }}>
                        RP
                    </div>
                    <div>
                        <h3 className="font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Reseller Platform</h3>
                        <p className="text-sm font-body" style={{ color: "var(--color-text-muted)" }}>
                            Multi-storefront — direct database ingestion for 500 storefronts
                        </p>
                    </div>
                </div>
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold font-body"
                    style={connected ? { backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)", border: "1px solid var(--color-accent-border)" }
                        : pending ? { backgroundColor: "rgba(245,158,11,0.1)", color: "#F59E0B", border: "1px solid rgba(245,158,11,0.3)" }
                            : { backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>
                    {connected && <CheckCircle2 className="w-3.5 h-3.5" />}
                    {connected ? (status === "syncing" ? "Syncing..." : "Connected") : pending ? "Pending Confirmation" : "Not connected"}
                </span>
            </div>

            {connected && (
                <div className="mt-5 grid grid-cols-2 gap-4">
                    {[
                        { label: "Last synced", value: fmt(integration!.last_sync_at) },
                        { label: "Storefronts", value: integration!.transaction_count.toLocaleString() },
                    ].map(s => (
                        <div key={s.label} className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                            <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>{s.label}</p>
                            <p className="mt-1 text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>{s.value}</p>
                        </div>
                    ))}
                </div>
            )}

            {/* Step 1: DB credentials form */}
            {step === "form" && (
                <form onSubmit={handleConnect} className="mt-5 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                        {[
                            { key: "db_host", label: "DB Host", placeholder: "db.example.com or IP", type: "text" },
                            { key: "db_name", label: "Database Name", placeholder: "wp_reseller_db", type: "text" },
                            { key: "db_user", label: "DB Username", placeholder: "db_user", type: "text" },
                            { key: "db_password", label: "DB Password", placeholder: "••••••••", type: "password" },
                        ].map(f => (
                            <div key={f.key} className="space-y-1">
                                <label className="text-xs font-semibold font-body" style={{ color: "var(--color-text-secondary)" }}>{f.label}</label>
                                <input type={f.type} placeholder={f.placeholder}
                                    value={(fields as any)[f.key]}
                                    onChange={e => setFields(v => ({ ...v, [f.key]: e.target.value }))} required
                                    className="w-full h-10 px-3 rounded-xl text-sm font-mono outline-none"
                                    style={{ backgroundColor: "var(--color-surface-raised)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" }}
                                    onFocus={e => e.currentTarget.style.boxShadow = "0 0 0 2px var(--color-accent-border)"}
                                    onBlur={e => e.currentTarget.style.boxShadow = "none"} />
                            </div>
                        ))}
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-semibold font-body" style={{ color: "var(--color-text-secondary)" }}>Table Prefix</label>
                        <input type="text" placeholder="wp_" value={fields.db_prefix}
                            onChange={e => setFields(v => ({ ...v, db_prefix: e.target.value }))}
                            className="w-40 h-10 px-3 rounded-xl text-sm font-mono outline-none"
                            style={{ backgroundColor: "var(--color-surface-raised)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" }}
                            onFocus={e => e.currentTarget.style.boxShadow = "0 0 0 2px var(--color-accent-border)"}
                            onBlur={e => e.currentTarget.style.boxShadow = "none"} />
                    </div>
                    {error && (
                        <div className="flex items-start gap-2 p-3 rounded-xl text-xs font-body"
                            style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#EF4444" }}>
                            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />{error}
                        </div>
                    )}
                    <div className="flex gap-3 pt-1">
                        <button type="button" onClick={() => { setStep("idle"); setError("") }}
                            className="flex-1 h-10 rounded-xl text-sm font-semibold font-body"
                            style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>Cancel</button>
                        <button type="submit" disabled={loading}
                            className="flex-1 h-10 rounded-xl text-sm font-bold font-body disabled:opacity-60"
                            style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                            {loading ? "Connecting..." : "Test Connection →"}
                        </button>
                    </div>
                </form>
            )}

            {/* Step 2: Confirmation */}
            {step === "preview" && preview && (
                <div className="mt-5 space-y-4">
                    <div className="p-4 rounded-xl space-y-3" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                        <p className="text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>
                            ✓ Connected — <span style={{ color: "var(--color-accent)" }}>{preview.storefronts_found} active storefronts</span> found
                        </p>
                        {preview.preview?.length > 0 && (
                            <div className="space-y-1">
                                <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Preview (first {preview.preview.length}):</p>
                                {preview.preview.map((sf: any) => (
                                    <p key={sf.id} className="text-xs font-mono" style={{ color: "var(--color-text-secondary)" }}>
                                        #{sf.id} — {sf.store_name} {sf.subdomain ? `(${sf.subdomain})` : ""}
                                    </p>
                                ))}
                            </div>
                        )}
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>
                            Confirming will create {preview.storefronts_found} brands in ORYNT and start syncing products + orders for each.
                        </p>
                    </div>
                    {error && (
                        <div className="flex items-start gap-2 p-3 rounded-xl text-xs font-body"
                            style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#EF4444" }}>
                            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />{error}
                        </div>
                    )}
                    <div className="flex gap-3">
                        <button onClick={() => { setStep("form"); setPreview(null); setError("") }}
                            className="flex-1 h-10 rounded-xl text-sm font-semibold font-body"
                            style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>Back</button>
                        <button onClick={handleConfirm} disabled={loading}
                            className="flex-1 h-10 rounded-xl text-sm font-bold font-body disabled:opacity-60"
                            style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                            {loading ? "Starting..." : `Confirm — Create ${preview.storefronts_found} Brands`}
                        </button>
                    </div>
                </div>
            )}

            {step === "syncing" && (
                <div className="mt-5 flex items-center gap-3 p-4 rounded-xl"
                    style={{ backgroundColor: "var(--color-accent-dim)", border: "1px solid var(--color-accent-border)" }}>
                    <RefreshCw className="w-4 h-4 animate-spin" style={{ color: "var(--color-accent)" }} />
                    <p className="text-sm font-semibold font-body" style={{ color: "var(--color-accent)" }}>
                        Brand creation in progress — check back in a few minutes.
                    </p>
                </div>
            )}

            {step === "idle" && !connected && (
                <div className="mt-5">
                    <button onClick={() => setStep("form")}
                        className="flex items-center gap-2 px-5 h-9 rounded-xl text-sm font-bold font-body"
                        style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                        <Plus className="w-4 h-4" /> Connect Reseller Platform
                    </button>
                </div>
            )}
            {step === "idle" && connected && (
                <div className="mt-5">
                    <button onClick={() => setStep("form")}
                        className="flex items-center gap-2 px-4 h-9 rounded-xl text-sm font-semibold font-body"
                        style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>
                        <RefreshCw className="w-3.5 h-3.5" /> Re-connect / Update Credentials
                    </button>
                </div>
            )}
        </div>
    )
}

// ── Preorder Platform Card ─────────────────────────────────────────────────────

function PreorderPlatformCard({ integration, brandId, onSuccess }: {
    integration: Integration | undefined; brandId: string; onSuccess: () => void
}) {
    const status = integration?.status
    const connected = status === "connected" || status === "syncing"
    const pending = status === "pending_confirmation"
    const fmt = (iso: string | null) => iso
        ? new Date(iso).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" }) : "Never"

    const [step, setStep] = useState<"idle" | "form" | "preview" | "syncing">(
        connected ? "idle" : pending ? "preview" : "idle"
    )
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")
    const [preview, setPreview] = useState<{ sellers_found: number; integration_id: string; preview: any[] } | null>(null)
    const [fields, setFields] = useState({ db_host: "", db_name: "", db_user: "", db_password: "" })

    const handleConnect = async (e: React.FormEvent) => {
        e.preventDefault(); setLoading(true); setError("")
        try {
            const res = await api.post("/api/integrations/preorder-platform/connect", { ...fields, brand_id: brandId })
            setPreview(res.data); setStep("preview")
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Connection failed. Check your database credentials.")
        } finally { setLoading(false) }
    }

    const handleConfirm = async () => {
        if (!preview) return
        setLoading(true); setError("")
        try {
            await api.post("/api/integrations/preorder-platform/confirm", {
                integration_id: preview.integration_id, brand_id: brandId
            })
            setStep("syncing"); onSuccess()
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Confirmation failed.")
        } finally { setLoading(false) }
    }

    return (
        <div className="rounded-2xl p-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold font-mono"
                        style={{ backgroundColor: connected ? "rgba(0,201,167,0.1)" : "var(--color-surface-raised)", color: connected ? "var(--color-accent)" : "var(--color-text-muted)" }}>
                        PO
                    </div>
                    <div>
                        <h3 className="font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Preorder Platform</h3>
                        <p className="text-sm font-body" style={{ color: "var(--color-text-muted)" }}>
                            Multi-seller preorder campaigns — direct database ingestion
                        </p>
                    </div>
                </div>
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold font-body"
                    style={connected
                        ? { backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)", border: "1px solid var(--color-accent-border)" }
                        : pending ? { backgroundColor: "rgba(245,158,11,0.1)", color: "#F59E0B", border: "1px solid rgba(245,158,11,0.3)" }
                            : { backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>
                    {connected && <CheckCircle2 className="w-3.5 h-3.5" />}
                    {connected ? (status === "syncing" ? "Syncing..." : "Connected") : pending ? "Pending Confirmation" : "Not connected"}
                </span>
            </div>

            {connected && (
                <div className="mt-5 grid grid-cols-2 gap-4">
                    {[
                        { label: "Last synced", value: fmt(integration!.last_sync_at) },
                        { label: "Seller brands", value: integration!.transaction_count.toLocaleString() },
                    ].map(s => (
                        <div key={s.label} className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                            <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>{s.label}</p>
                            <p className="mt-1 text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>{s.value}</p>
                        </div>
                    ))}
                </div>
            )}

            {step === "form" && (
                <form onSubmit={handleConnect} className="mt-5 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                        {[
                            { key: "db_host", label: "DB Host", placeholder: "db.example.com or IP", type: "text" },
                            { key: "db_name", label: "Database Name", placeholder: "preorder_db", type: "text" },
                            { key: "db_user", label: "DB Username", placeholder: "db_user", type: "text" },
                            { key: "db_password", label: "DB Password", placeholder: "••••••••", type: "password" },
                        ].map(f => (
                            <div key={f.key} className="space-y-1">
                                <label className="text-xs font-semibold font-body" style={{ color: "var(--color-text-secondary)" }}>{f.label}</label>
                                <input type={f.type} placeholder={f.placeholder} required
                                    value={(fields as any)[f.key]}
                                    onChange={e => setFields(v => ({ ...v, [f.key]: e.target.value }))}
                                    className="w-full h-10 px-3 rounded-xl text-sm font-mono outline-none"
                                    style={{ backgroundColor: "var(--color-surface-raised)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" }}
                                    onFocus={e => e.currentTarget.style.boxShadow = "0 0 0 2px var(--color-accent-border)"}
                                    onBlur={e => e.currentTarget.style.boxShadow = "none"} />
                            </div>
                        ))}
                    </div>
                    {error && (
                        <div className="flex items-start gap-2 p-3 rounded-xl text-xs font-body"
                            style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#EF4444" }}>
                            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />{error}
                        </div>
                    )}
                    <div className="flex gap-3 pt-1">
                        <button type="button" onClick={() => { setStep("idle"); setError("") }}
                            className="flex-1 h-10 rounded-xl text-sm font-semibold font-body"
                            style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>Cancel</button>
                        <button type="submit" disabled={loading}
                            className="flex-1 h-10 rounded-xl text-sm font-bold font-body disabled:opacity-60"
                            style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                            {loading ? "Connecting..." : "Test Connection →"}
                        </button>
                    </div>
                </form>
            )}

            {step === "preview" && preview && (
                <div className="mt-5 space-y-4">
                    <div className="p-4 rounded-xl space-y-3" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                        <p className="text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>
                            ✓ Connected — <span style={{ color: "var(--color-accent)" }}>{preview.sellers_found} active sellers</span> found
                        </p>
                        {preview.preview?.length > 0 && (
                            <div className="space-y-1">
                                <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Preview (first {preview.preview.length}):</p>
                                {preview.preview.map((s: any) => (
                                    <p key={s.id} className="text-xs font-mono" style={{ color: "var(--color-text-secondary)" }}>
                                        #{s.id} — {s.business_name}
                                        {s.total_campaigns ? ` | ${s.total_campaigns} campaigns` : ""}
                                        {s.reliability_score ? ` | ⭐ ${Number(s.reliability_score).toFixed(1)}` : ""}
                                    </p>
                                ))}
                            </div>
                        )}
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>
                            Confirming will create {preview.sellers_found} brands and sync all campaigns, orders, and customers.
                        </p>
                    </div>
                    {error && (
                        <div className="flex items-start gap-2 p-3 rounded-xl text-xs font-body"
                            style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#EF4444" }}>
                            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />{error}
                        </div>
                    )}
                    <div className="flex gap-3">
                        <button onClick={() => { setStep("form"); setPreview(null); setError("") }}
                            className="flex-1 h-10 rounded-xl text-sm font-semibold font-body"
                            style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>Back</button>
                        <button onClick={handleConfirm} disabled={loading}
                            className="flex-1 h-10 rounded-xl text-sm font-bold font-body disabled:opacity-60"
                            style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                            {loading ? "Starting..." : `Confirm — Create ${preview.sellers_found} Brands`}
                        </button>
                    </div>
                </div>
            )}

            {step === "syncing" && (
                <div className="mt-5 flex items-center gap-3 p-4 rounded-xl"
                    style={{ backgroundColor: "var(--color-accent-dim)", border: "1px solid var(--color-accent-border)" }}>
                    <RefreshCw className="w-4 h-4 animate-spin" style={{ color: "var(--color-accent)" }} />
                    <p className="text-sm font-semibold font-body" style={{ color: "var(--color-accent)" }}>
                        Brand creation in progress — check back in a few minutes.
                    </p>
                </div>
            )}

            {step === "idle" && !connected && (
                <div className="mt-5">
                    <button onClick={() => setStep("form")}
                        className="flex items-center gap-2 px-5 h-9 rounded-xl text-sm font-bold font-body"
                        style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                        <Plus className="w-4 h-4" /> Connect Preorder Platform
                    </button>
                </div>
            )}
            {step === "idle" && connected && (
                <div className="mt-5">
                    <button onClick={() => setStep("form")}
                        className="flex items-center gap-2 px-4 h-9 rounded-xl text-sm font-semibold font-body"
                        style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>
                        <RefreshCw className="w-3.5 h-3.5" /> Re-connect / Update Credentials
                    </button>
                </div>
            )}
        </div>
    )
}

// ── Meta Ads Card ─────────────────────────────────────────────────────────────

function MetaAdsCard({ integration, brandId, onSuccess }: {
    integration: Integration | undefined; brandId: string; onSuccess: () => void
}) {
    const connected = integration?.status === "connected"
    const fmt = (iso: string | null) => iso ? new Date(iso).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" }) : "Never"

    const handleOAuth = () => {
        window.location.href = `/api/integrations/meta-ads/auth?brand_id=${brandId}`
    }

    return (
        <div className="rounded-2xl p-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center"
                        style={{ backgroundColor: connected ? "rgba(24,119,242,0.12)" : "var(--color-surface-raised)" }}>
                        <BarChart2 className="w-6 h-6" style={{ color: connected ? "#1877F2" : "var(--color-text-muted)" }} />
                    </div>
                    <div>
                        <h3 className="font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Meta Ads</h3>
                        <p className="text-sm font-body" style={{ color: "var(--color-text-muted)" }}>Facebook &amp; Instagram campaign performance · ROAS</p>
                    </div>
                </div>
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold font-body"
                    style={connected
                        ? { backgroundColor: "rgba(24,119,242,0.1)", color: "#1877F2", border: "1px solid rgba(24,119,242,0.3)" }
                        : { backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>
                    {connected && <CheckCircle2 className="w-3.5 h-3.5" />}
                    {connected ? "Connected" : "Not connected"}
                </span>
            </div>

            {connected && (
                <div className="mt-5 grid grid-cols-2 gap-4">
                    {[
                        { label: "Last synced", value: fmt(integration!.last_sync_at) },
                        { label: "Days synced", value: (integration!.transaction_count || 0).toLocaleString() },
                    ].map(s => (
                        <div key={s.label} className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                            <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>{s.label}</p>
                            <p className="mt-1 text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>{s.value}</p>
                        </div>
                    ))}
                </div>
            )}

            <div className="mt-5">
                <button onClick={handleOAuth}
                    className="flex items-center gap-2 px-5 h-9 rounded-xl text-sm font-bold font-body"
                    style={connected
                        ? { border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }
                        : { backgroundColor: "#1877F2", color: "#ffffff" }}>
                    <ExternalLink className="w-4 h-4" />
                    {connected ? "Reconnect Meta Ads" : "Connect via Meta Business Login →"}
                </button>
            </div>
        </div>
    )
}

// ── Selar Card ────────────────────────────────────────────────────────────────

function SelarCard({ integration, brandId, onSuccess }: {
    integration: Integration | undefined; brandId: string; onSuccess: () => void
}) {
    const status = integration?.status
    const connected = status === "connected"
    const fmt = (iso: string | null) => iso ? new Date(iso).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" }) : "Never"
    const [showForm, setShowForm] = useState(false)
    const [apiKey, setApiKey] = useState("")
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")

    const handleConnect = async (e: React.FormEvent) => {
        e.preventDefault(); setLoading(true); setError("")
        try {
            await api.post("/api/integrations/selar/connect", { api_key: apiKey, brand_id: brandId })
            setShowForm(false); setApiKey(""); onSuccess()
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Connection failed. Check your API key.")
        } finally { setLoading(false) }
    }

    return (
        <div className="rounded-2xl p-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center font-bold text-sm font-mono"
                        style={{ backgroundColor: connected ? "rgba(0,201,167,0.1)" : "var(--color-surface-raised)", color: connected ? "var(--color-accent)" : "var(--color-text-muted)" }}>
                        SLR
                    </div>
                    <div>
                        <h3 className="font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Selar</h3>
                        <p className="text-sm font-body" style={{ color: "var(--color-text-muted)" }}>Digital products — ebooks, courses, templates (is_digital = true)</p>
                    </div>
                </div>
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold font-body"
                    style={connected
                        ? { backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)", border: "1px solid var(--color-accent-border)" }
                        : { backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>
                    {connected && <CheckCircle2 className="w-3.5 h-3.5" />}
                    {connected ? "Connected" : "Not connected"}
                </span>
            </div>

            {connected && (
                <div className="mt-5 grid grid-cols-2 gap-4">
                    {[
                        { label: "Last synced", value: fmt(integration!.last_sync_at) },
                        { label: "Orders synced", value: (integration!.transaction_count || 0).toLocaleString() },
                    ].map(s => (
                        <div key={s.label} className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                            <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>{s.label}</p>
                            <p className="mt-1 text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>{s.value}</p>
                        </div>
                    ))}
                </div>
            )}

            {showForm && (
                <form onSubmit={handleConnect} className="mt-5 space-y-3">
                    <div className="space-y-1">
                        <label className="text-xs font-semibold font-body" style={{ color: "var(--color-text-secondary)" }}>
                            Selar API Key <span className="font-normal text-xs" style={{ color: "var(--color-text-muted)" }}>(Settings → API Keys in your Selar dashboard)</span>
                        </label>
                        <input type="password" required placeholder="sk_live_..." value={apiKey}
                            onChange={e => setApiKey(e.target.value)}
                            className="w-full h-10 px-3 rounded-xl text-sm font-mono outline-none"
                            style={{ backgroundColor: "var(--color-surface-raised)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" }}
                            onFocus={e => e.currentTarget.style.boxShadow = "0 0 0 2px var(--color-accent-border)"}
                            onBlur={e => e.currentTarget.style.boxShadow = "none"} />
                    </div>
                    {error && (
                        <div className="flex items-start gap-2 p-3 rounded-xl text-xs font-body"
                            style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#EF4444" }}>
                            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />{error}
                        </div>
                    )}
                    <div className="flex gap-3 pt-1">
                        <button type="button" onClick={() => { setShowForm(false); setError("") }}
                            className="flex-1 h-10 rounded-xl text-sm font-semibold font-body"
                            style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>Cancel</button>
                        <button type="submit" disabled={loading}
                            className="flex-1 h-10 rounded-xl text-sm font-bold font-body disabled:opacity-60"
                            style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                            {loading ? "Connecting..." : "Connect Selar →"}
                        </button>
                    </div>
                </form>
            )}

            {!showForm && (
                <div className="mt-5">
                    <button onClick={() => setShowForm(true)}
                        className="flex items-center gap-2 px-5 h-9 rounded-xl text-sm font-bold font-body"
                        style={connected
                            ? { border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }
                            : { backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                        {connected ? <><RefreshCw className="w-3.5 h-3.5" /> Reconnect</> : <><Plus className="w-4 h-4" /> Connect Selar</>}
                    </button>
                </div>
            )}
        </div>
    )
}

// ── Gumroad Card ──────────────────────────────────────────────────────────────

function GumroadCard({ integration, brandId, onSuccess }: {
    integration: Integration | undefined; brandId: string; onSuccess: () => void
}) {
    const status = integration?.status
    const connected = status === "connected"
    const fmt = (iso: string | null) => iso ? new Date(iso).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" }) : "Never"

    const handleOAuth = () => {
        window.location.href = `/api/integrations/gumroad/auth?brand_id=${brandId}`
    }

    return (
        <div className="rounded-2xl p-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center font-bold text-xs font-mono"
                        style={{ backgroundColor: connected ? "rgba(255,144,232,0.15)" : "var(--color-surface-raised)", color: connected ? "#ff90e8" : "var(--color-text-muted)" }}>
                        GUM
                    </div>
                    <div>
                        <h3 className="font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Gumroad</h3>
                        <p className="text-sm font-body" style={{ color: "var(--color-text-muted)" }}>Digital products via OAuth — is_digital = true</p>
                    </div>
                </div>
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold font-body"
                    style={connected
                        ? { backgroundColor: "rgba(255,144,232,0.1)", color: "#ff90e8", border: "1px solid rgba(255,144,232,0.3)" }
                        : { backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>
                    {connected && <CheckCircle2 className="w-3.5 h-3.5" />}
                    {connected ? "Connected" : "Not connected"}
                </span>
            </div>

            {connected && (
                <div className="mt-5 grid grid-cols-2 gap-4">
                    {[
                        { label: "Last synced", value: fmt(integration!.last_sync_at) },
                        { label: "Sales synced", value: (integration!.transaction_count || 0).toLocaleString() },
                    ].map(s => (
                        <div key={s.label} className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                            <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>{s.label}</p>
                            <p className="mt-1 text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>{s.value}</p>
                        </div>
                    ))}
                </div>
            )}

            <div className="mt-5">
                <button onClick={handleOAuth}
                    className="flex items-center gap-2 px-5 h-9 rounded-xl text-sm font-bold font-body"
                    style={connected
                        ? { border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }
                        : { backgroundColor: "#ff90e8", color: "#1a0020" }}>
                    <ExternalLink className="w-4 h-4" />
                    {connected ? "Reconnect via Gumroad" : "Connect via Gumroad OAuth →"}
                </button>
            </div>
        </div>
    )
}

// ── Bumpa Import Card ─────────────────────────────────────────────────────────

function BumpaImportCard({ brandId }: { brandId: string }) {
    const [dragging, setDragging] = useState(false)
    const [uploading, setUploading] = useState(false)
    const [result, setResult] = useState<{
        orders_imported: number; products_imported: number;
        customers_imported: number; errors: string[]; total_errors: number
    } | null>(null)
    const [uploadError, setUploadError] = useState("")
    const fileRef = useRef<HTMLInputElement>(null)

    const downloadTemplate = async () => {
        const link = document.createElement("a")
        link.href = `/api/integrations/bumpa/template`
        link.download = "bumpa_import_template.csv"
        // Pass auth header via fetch then create blob URL
        try {
            const token = localStorage.getItem("access_token")
            const res = await fetch("/api/integrations/bumpa/template", {
                headers: token ? { Authorization: `Bearer ${token}` } : {}
            })
            const blob = await res.blob()
            link.href = URL.createObjectURL(blob)
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
        } catch {
            link.click()  // fallback
        }
    }

    const handleFile = async (f: File) => {
        if (!f.name.endsWith(".csv")) {
            setUploadError("Please upload a .csv file"); return
        }
        setUploading(true); setResult(null); setUploadError("")
        try {
            const fd = new FormData()
            fd.append("brand_id", brandId)
            fd.append("file", f)
            const res = await api.post("/api/integrations/bumpa/upload", fd, {
                headers: { "Content-Type": "multipart/form-data" }
            })
            setResult(res.data)
        } catch (err: any) {
            setUploadError(err?.response?.data?.detail || "Upload failed. Please check your CSV and try again.")
        } finally { setUploading(false) }
    }

    const onDrop = (e: React.DragEvent) => {
        e.preventDefault(); setDragging(false)
        const f = e.dataTransfer.files[0]
        if (f) handleFile(f)
    }

    return (
        <div className="rounded-2xl p-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            {/* Header */}
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center font-bold text-sm font-mono"
                        style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-muted)" }}>
                        CSV
                    </div>
                    <div>
                        <h3 className="font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Import from Bumpa</h3>
                        <p className="text-sm font-body" style={{ color: "var(--color-text-muted)" }}>
                            Upload your Bumpa CSV export to import orders, products and customers
                        </p>
                    </div>
                </div>
                <button onClick={downloadTemplate}
                    className="flex items-center gap-2 px-4 h-9 rounded-xl text-xs font-semibold font-body flex-shrink-0"
                    style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>
                    <ExternalLink className="w-3.5 h-3.5" /> Download Template
                </button>
            </div>

            {/* Drag-drop zone */}
            <div
                onDragOver={e => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                onClick={() => !uploading && fileRef.current?.click()}
                className="mt-5 rounded-xl border-2 border-dashed flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors"
                style={{
                    height: 120,
                    borderColor: dragging ? "var(--color-accent)" : "var(--color-border)",
                    backgroundColor: dragging ? "var(--color-accent-dim)" : "var(--color-surface-raised)",
                }}>
                <input ref={fileRef} type="file" accept=".csv" className="hidden"
                    onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }} />
                {uploading
                    ? <><RefreshCw className="w-6 h-6 animate-spin" style={{ color: "var(--color-accent)" }} />
                        <p className="text-sm font-semibold font-body" style={{ color: "var(--color-accent)" }}>Importing...</p></>
                    : <><ShoppingBag className="w-6 h-6" style={{ color: "var(--color-text-muted)" }} />
                        <p className="text-sm font-body" style={{ color: "var(--color-text-muted)" }}>
                            Drag &amp; drop your CSV here, or <span style={{ color: "var(--color-accent)" }}>click to browse</span>
                        </p>
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Bumpa CSV export format only</p></>
                }
            </div>

            {/* Upload error */}
            {uploadError && (
                <div className="mt-4 flex items-start gap-2 p-3 rounded-xl text-xs font-body"
                    style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#EF4444" }}>
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />{uploadError}
                </div>
            )}

            {/* Import result */}
            {result && (
                <div className="mt-4 space-y-3">
                    {/* Summary stats */}
                    <div className="grid grid-cols-3 gap-3">
                        {[
                            { label: "Orders", value: result.orders_imported },
                            { label: "Products", value: result.products_imported },
                            { label: "Customers", value: result.customers_imported },
                        ].map(s => (
                            <div key={s.label} className="rounded-xl p-3 text-center" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                                <p className="text-xl font-bold font-display" style={{ color: "var(--color-accent)" }}>{s.value}</p>
                                <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>{s.label} imported</p>
                            </div>
                        ))}
                    </div>

                    {/* Errors */}
                    {result.errors.length > 0 && (
                        <div className="rounded-xl p-4 space-y-2"
                            style={{ backgroundColor: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.25)" }}>
                            <p className="text-xs font-semibold font-body" style={{ color: "#F59E0B" }}>
                                {result.total_errors} row{result.total_errors !== 1 ? "s" : ""} had issues (these rows were skipped):
                            </p>
                            <div className="space-y-1 max-h-40 overflow-y-auto">
                                {result.errors.slice(0, 10).map((e, i) => (
                                    <p key={i} className="text-xs font-mono" style={{ color: "var(--color-text-secondary)" }}>• {e}</p>
                                ))}
                                {result.total_errors > 10 && (
                                    <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>
                                        ...and {result.total_errors - 10} more. Fix these rows in your CSV and re-upload.
                                    </p>
                                )}
                            </div>
                        </div>
                    )}

                    {result.orders_imported > 0 && (
                        <div className="flex items-center gap-2 p-3 rounded-xl"
                            style={{ backgroundColor: "var(--color-accent-dim)", border: "1px solid var(--color-accent-border)" }}>
                            <CheckCircle2 className="w-4 h-4 flex-shrink-0" style={{ color: "var(--color-accent)" }} />
                            <p className="text-sm font-semibold font-body" style={{ color: "var(--color-accent)" }}>
                                Import complete. Re-uploading the same file will not create duplicates.
                            </p>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

// ── Page (inner) ──────────────────────────────────────────────────────────────


function IntegrationsInner() {
    const { activeBrandId } = useAuthStore()
    const [integrations, setIntegrations] = useState<Integration[]>([])
    const [modal, setModal] = useState<GatewayKey | null>(null)
    const [ecomModal, setEcomModal] = useState<EcommerceKey | null>(null)
    const [shopifySuccess, setShopifySuccess] = useState("")
    const searchParams = useSearchParams()

    const load = async () => {
        if (!activeBrandId) return
        try { const res = await api.get(`/api/integrations?brand_id=${activeBrandId}`); setIntegrations(res.data) }
        catch { setIntegrations([]) }
    }

    useEffect(() => { load() }, [activeBrandId])
    useEffect(() => {
        if (searchParams?.get("shopify") === "connected") {
            setShopifySuccess(`Shopify store "${searchParams.get("shop")}" connected! Sync running in background.`)
            load()
        }
    }, [searchParams])

    const find = (type: string) => integrations.find(i => i.type === type)

    return (
        <div className="p-8 max-w-3xl space-y-6">
            <div>
                <h1 className="text-2xl font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Integrations</h1>
                <p className="mt-1 text-sm font-body" style={{ color: "var(--color-text-muted)" }}>
                    Connect your payment gateways, stores, and bank accounts to import orders automatically.
                </p>
            </div>

            {shopifySuccess && (
                <div className="flex items-center gap-3 p-4 rounded-xl" style={{ backgroundColor: "var(--color-accent-dim)", border: "1px solid var(--color-accent-border)" }}>
                    <CheckCircle2 className="w-5 h-5 flex-shrink-0" style={{ color: "var(--color-accent)" }} />
                    <p className="text-sm font-semibold font-body" style={{ color: "var(--color-accent)" }}>{shopifySuccess}</p>
                    <button onClick={() => setShopifySuccess("")} className="ml-auto text-xs font-body" style={{ color: "var(--color-text-muted)" }}>✕</button>
                </div>
            )}

            <div>
                <h2 className="text-xs font-bold uppercase tracking-widest mb-4 font-body" style={{ color: "var(--color-text-muted)" }}>E-Commerce</h2>
                <div className="space-y-4">
                    {activeBrandId && <ShopifyCard integration={find("shopify")} brandId={activeBrandId} onSuccess={load} />}
                    {(Object.keys(ECOMMERCE_GATEWAYS) as EcommerceKey[]).map(key => (
                        <GatewayCard key={key} gatewayKey={key as any} integration={find(key)}
                            onConnect={() => setEcomModal(key)}
                            config={ECOMMERCE_GATEWAYS[key]} />
                    ))}
                    {activeBrandId && <ResellerPlatformCard integration={find("reseller_platform")} brandId={activeBrandId} onSuccess={load} />}
                    {activeBrandId && <PreorderPlatformCard integration={find("preorder_platform")} brandId={activeBrandId} onSuccess={load} />}
                    {activeBrandId && <SelarCard integration={find("selar")} brandId={activeBrandId} onSuccess={load} />}
                    {activeBrandId && <GumroadCard integration={find("gumroad")} brandId={activeBrandId} onSuccess={load} />}
                </div>
            </div>

            <div>
                <h2 className="text-xs font-bold uppercase tracking-widest mb-4 font-body" style={{ color: "var(--color-text-muted)" }}>Payment Gateways</h2>
                <div className="space-y-4">
                    {(Object.keys(PAYMENT_GATEWAYS) as GatewayKey[]).map(key => (
                        <GatewayCard key={key} gatewayKey={key} integration={find(key)} onConnect={() => setModal(key)} />
                    ))}
                </div>
            </div>

            <div>
                <h2 className="text-xs font-bold uppercase tracking-widest mb-4 font-body" style={{ color: "var(--color-text-muted)" }}>Open Banking</h2>
                {activeBrandId && <MonoBankCard integration={find("mono")} brandId={activeBrandId} onSuccess={load} />}
            </div>

            <div>
                <h2 className="text-xs font-bold uppercase tracking-widest mb-4 font-body" style={{ color: "var(--color-text-muted)" }}>Ads</h2>
                <div className="space-y-4">
                    {activeBrandId && <MetaAdsCard integration={find("meta_ads")} brandId={activeBrandId} onSuccess={load} />}
                </div>
            </div>

            <div>
                <h2 className="text-xs font-bold uppercase tracking-widest mb-4 font-body" style={{ color: "var(--color-text-muted)" }}>CSV Import</h2>
                <div className="space-y-4">
                    {activeBrandId && <BumpaImportCard brandId={activeBrandId} />}
                </div>
            </div>

            {modal && activeBrandId && (
                <ConnectModal gateway={modal} brandId={activeBrandId} onClose={() => setModal(null)} onSuccess={load} />
            )}
            {ecomModal && activeBrandId && (
                <ConnectModal gateway={ecomModal} brandId={activeBrandId} onClose={() => setEcomModal(null)} onSuccess={load}
                    config={ECOMMERCE_GATEWAYS[ecomModal]} />
            )}
        </div>
    )
}

export default function IntegrationsPage() {
    return <Suspense fallback={<div className="p-8" style={{ color: "var(--color-text-muted)" }}>Loading...</div>}><IntegrationsInner /></Suspense>
}
