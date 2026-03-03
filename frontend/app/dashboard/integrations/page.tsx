"use client"

import { useState, useEffect, useRef } from "react"
import { CheckCircle2, AlertCircle, Plus, RefreshCw, Zap, Building2, ExternalLink } from "lucide-react"
import { useAuthStore } from "@/store/auth"
import api from "@/lib/api"

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
        fields: [
            { name: "secret_key", label: "Secret Key", placeholder: "sk_live_... or sk_test_...", type: "password" },
        ],
        hint: "Paystack Dashboard → Settings → API Keys & Webhooks",
    },
    flutterwave: {
        label: "Flutterwave",
        description: "Payment gateway — Pan-African, 30+ currencies",
        endpoint: "/api/integrations/flutterwave/connect",
        fields: [
            { name: "secret_key", label: "Secret Key", placeholder: "FLWSECK_TEST-... or FLWSECK-...", type: "password" },
        ],
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

type GatewayKey = keyof typeof PAYMENT_GATEWAYS

// ── Connect Modal (payment gateways) ─────────────────────────────────────────

function ConnectModal({ gateway, onClose, onSuccess, brandId }: {
    gateway: GatewayKey; onClose: () => void; onSuccess: () => void; brandId: string
}) {
    const meta = PAYMENT_GATEWAYS[gateway]
    const [values, setValues] = useState<Record<string, string>>({})
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")
    const [success, setSuccess] = useState(false)

    const handleConnect = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true); setError("")
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
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Your credentials are encrypted and stored securely</p>
                    </div>
                </div>
                {success ? (
                    <div className="flex items-center gap-3 p-4 rounded-xl" style={{ backgroundColor: "var(--color-accent-dim)", border: "1px solid var(--color-accent-border)" }}>
                        <CheckCircle2 className="w-5 h-5 flex-shrink-0" style={{ color: "var(--color-accent)" }} />
                        <div>
                            <p className="text-sm font-semibold font-body" style={{ color: "var(--color-accent)" }}>Connected successfully!</p>
                            <p className="text-xs font-body" style={{ color: "var(--color-text-secondary)" }}>Historical sync started in the background.</p>
                        </div>
                    </div>
                ) : (
                    <form onSubmit={handleConnect} className="space-y-4">
                        {meta.fields.map(field => (
                            <div key={field.name} className="space-y-1.5">
                                <label className="block text-xs font-semibold font-body" style={{ color: "var(--color-text-secondary)" }}>{field.label}</label>
                                <input type={field.type} placeholder={field.placeholder}
                                    value={values[field.name] ?? ""}
                                    onChange={e => setValues(v => ({ ...v, [field.name]: e.target.value }))}
                                    required
                                    className="w-full h-11 px-4 rounded-xl text-sm font-mono outline-none transition-shadow"
                                    style={{ backgroundColor: "var(--color-surface-raised)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)", caretColor: "var(--color-accent)" }}
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

// ── Mono Connect Widget ───────────────────────────────────────────────────────

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
        api.get(`/api/orders/inbox?brand_id=${brandId}&page_size=1`).then(r => {
            setPendingCount(r.data.total)
        }).catch(() => {})
    }, [connected, brandId])

    const handleConnect = async () => {
        setLoading(true); setError("")
        try {
            // 1. Get Mono Connect URL/token
            const res = await api.post("/api/integrations/mono/initiate", { brand_id: brandId })
            const monoUrl = res.data.mono_url

            if (!monoUrl) {
                setError("Could not get Mono Connect URL. Ensure MONO_SECRET_KEY is set in backend .env.")
                setLoading(false)
                return
            }

            // 2. Open Mono Connect widget in a popup
            const popup = window.open(monoUrl, "mono_connect",
                "width=500,height=700,top=100,left=200,scrollbars=yes")

            // 3. Listen for the mono success message from the popup
            const handler = async (event: MessageEvent) => {
                if (event.data?.type === "mono.connect.widget.account_linked" ||
                    event.data?.type === "mono.events.account_linked") {
                    const code = event.data?.data?.code
                    popup?.close()
                    window.removeEventListener("message", handler)

                    if (code) {
                        try {
                            await api.post("/api/integrations/mono/exchange", { code, brand_id: brandId })
                            onSuccess()
                        } catch (err: any) {
                            setError(err?.response?.data?.detail || "Failed to link bank account.")
                        }
                    }
                    setLoading(false)
                }
            }
            window.addEventListener("message", handler)

            // Timeout if popup closed without success
            const checkClosed = setInterval(() => {
                if (popup?.closed) {
                    clearInterval(checkClosed)
                    window.removeEventListener("message", handler)
                    setLoading(false)
                }
            }, 1000)
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Failed to initiate Mono Connect.")
            setLoading(false)
        }
    }

    return (
        <div className="rounded-2xl p-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center"
                        style={{ backgroundColor: connected ? "rgba(0,201,167,0.1)" : "var(--color-surface-raised)" }}>
                        <Building2 className="w-6 h-6" style={{ color: connected ? "var(--color-accent)" : "var(--color-text-muted)" }} />
                    </div>
                    <div>
                        <h3 className="font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Bank Account (Mono)</h3>
                        <p className="text-sm font-body" style={{ color: "var(--color-text-muted)" }}>
                            Import bank transfers — converts credits to Order Inbox items
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
                <div className="mt-5 grid grid-cols-2 gap-4">
                    <div className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Last synced</p>
                        <p className="mt-1 text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>{fmt(integration!.last_sync_at)}</p>
                    </div>
                    <div className="rounded-xl p-4 cursor-pointer" style={{ backgroundColor: pendingCount ? "rgba(245,158,11,0.1)" : "var(--color-surface-raised)", border: pendingCount ? "1px solid rgba(245,158,11,0.3)" : "none" }}
                        onClick={() => pendingCount && (window.location.href = "/dashboard/orders/inbox")}>
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Unmatched transfers</p>
                        <p className="mt-1 text-sm font-semibold font-body" style={{ color: pendingCount ? "#F59E0B" : "var(--color-text-primary)" }}>
                            {pendingCount ?? "—"} {pendingCount ? "→ Review" : ""}
                        </p>
                    </div>
                </div>
            )}

            {error && (
                <div className="mt-4 flex items-start gap-2 p-3 rounded-xl text-xs font-body"
                    style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#EF4444" }}>
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />{error}
                </div>
            )}

            <div className="mt-5 flex items-center gap-3">
                <button onClick={handleConnect} disabled={loading}
                    className="flex items-center gap-2 px-5 h-9 rounded-xl text-sm font-bold font-body disabled:opacity-60"
                    style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                    {loading ? "Opening..." : connected ? <><RefreshCw className="w-3.5 h-3.5" /> Re-connect Bank</> : <><Plus className="w-4 h-4" /> Connect Bank Account</>}
                </button>
                {connected && (
                    <a href="/dashboard/orders/inbox"
                        className="flex items-center gap-1.5 text-sm font-semibold font-body"
                        style={{ color: "var(--color-accent)" }}>
                        <ExternalLink className="w-4 h-4" /> Order Inbox
                    </a>
                )}
            </div>
        </div>
    )
}

// ── Gateway Card ──────────────────────────────────────────────────────────────

function GatewayCard({ gatewayKey, integration, onConnect, available }: {
    gatewayKey: GatewayKey; integration: Integration | undefined; onConnect: () => void; available: boolean
}) {
    const meta = PAYMENT_GATEWAYS[gatewayKey]
    const connected = integration?.status === "connected"
    const fmt = (iso: string | null) => iso
        ? new Date(iso).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" }) : "Never"

    return (
        <div className={`rounded-2xl p-6 ${!available ? "opacity-50" : ""}`}
            style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
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
                <div className="mt-5 grid grid-cols-2 gap-4">
                    {[
                        { label: "Last synced", value: fmt(integration!.last_sync_at) },
                        { label: "Orders imported", value: integration!.transaction_count.toLocaleString() },
                    ].map(s => (
                        <div key={s.label} className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                            <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>{s.label}</p>
                            <p className="mt-1 text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>{s.value}</p>
                        </div>
                    ))}
                </div>
            )}
            {available && (
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
            )}
        </div>
    )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function IntegrationsPage() {
    const { activeBrandId } = useAuthStore()
    const [integrations, setIntegrations] = useState<Integration[]>([])
    const [modal, setModal] = useState<GatewayKey | null>(null)

    const load = async () => {
        if (!activeBrandId) return
        try {
            const res = await api.get(`/api/integrations?brand_id=${activeBrandId}`)
            setIntegrations(res.data)
        } catch { setIntegrations([]) }
    }
    useEffect(() => { load() }, [activeBrandId])
    const find = (type: string) => integrations.find(i => i.type === type)

    return (
        <div className="p-8 max-w-3xl space-y-6">
            <div>
                <h1 className="text-2xl font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Integrations</h1>
                <p className="mt-1 text-sm font-body" style={{ color: "var(--color-text-muted)" }}>
                    Connect your payment gateways and bank accounts to automatically import orders.
                </p>
            </div>

            <div>
                <h2 className="text-xs font-bold uppercase tracking-widest mb-4 font-body" style={{ color: "var(--color-text-muted)" }}>
                    Payment Gateways
                </h2>
                <div className="space-y-4">
                    {(Object.keys(PAYMENT_GATEWAYS) as GatewayKey[]).map(key => (
                        <GatewayCard key={key} gatewayKey={key} integration={find(key)}
                            onConnect={() => setModal(key)} available={true} />
                    ))}
                </div>
            </div>

            <div>
                <h2 className="text-xs font-bold uppercase tracking-widest mb-4 font-body" style={{ color: "var(--color-text-muted)" }}>
                    Open Banking
                </h2>
                {activeBrandId && (
                    <MonoBankCard integration={find("mono")} brandId={activeBrandId} onSuccess={load} />
                )}
            </div>

            {modal && activeBrandId && (
                <ConnectModal gateway={modal} brandId={activeBrandId}
                    onClose={() => setModal(null)} onSuccess={load} />
            )}
        </div>
    )
}
