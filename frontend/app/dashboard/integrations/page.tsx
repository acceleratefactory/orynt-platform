"use client"

import { useState, useEffect } from "react"
import { CheckCircle2, AlertCircle, Plus, RefreshCw, Zap } from "lucide-react"
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

interface ConnectModalProps {
    gateway: "paystack" | "flutterwave"
    onClose: () => void
    onSuccess: () => void
    brandId: string
}

const GATEWAY_META = {
    paystack: {
        label: "Paystack",
        placeholder: "sk_live_... or sk_test_...",
        hint: "Find this in Paystack Dashboard → Settings → API Keys & Webhooks",
        keyPrefix: "sk_",
        endpoint: "/api/integrations/paystack/connect",
    },
    flutterwave: {
        label: "Flutterwave",
        placeholder: "FLWSECK_TEST-... or FLWSECK-...",
        hint: "Find this in Flutterwave Dashboard → Settings → API Keys",
        keyPrefix: "FLW",
        endpoint: "/api/integrations/flutterwave/connect",
    },
}

function ConnectModal({ gateway, onClose, onSuccess, brandId }: ConnectModalProps) {
    const meta = GATEWAY_META[gateway]
    const [secretKey, setSecretKey] = useState("")
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")
    const [success, setSuccess] = useState(false)

    const handleConnect = async (e: React.FormEvent) => {
        e.preventDefault()
        const trimmed = secretKey.trim()
        if (!trimmed.startsWith(meta.keyPrefix)) {
            setError(`Key must start with "${meta.keyPrefix}..."`)
            return
        }
        setLoading(true)
        setError("")
        try {
            await api.post(meta.endpoint, { secret_key: trimmed, brand_id: brandId })
            setSuccess(true)
            setTimeout(() => { onSuccess(); onClose() }, 1800)
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Failed to connect. Check your key and try again.")
        } finally {
            setLoading(false)
        }
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
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Your key is encrypted and stored securely</p>
                    </div>
                </div>

                {success ? (
                    <div className="flex items-center gap-3 p-4 rounded-xl" style={{ backgroundColor: "var(--color-accent-dim)", border: "1px solid var(--color-accent-border)" }}>
                        <CheckCircle2 className="w-5 h-5 flex-shrink-0" style={{ color: "var(--color-accent)" }} />
                        <div>
                            <p className="text-sm font-semibold font-body" style={{ color: "var(--color-accent)" }}>Connected successfully!</p>
                            <p className="text-xs font-body" style={{ color: "var(--color-text-secondary)" }}>Historical sync has started in the background.</p>
                        </div>
                    </div>
                ) : (
                    <form onSubmit={handleConnect} className="space-y-4">
                        <div className="space-y-2">
                            <label className="block text-xs font-semibold font-body" style={{ color: "var(--color-text-secondary)" }}>
                                {meta.label} Secret Key
                            </label>
                            <input
                                type="password"
                                placeholder={meta.placeholder}
                                value={secretKey}
                                onChange={e => setSecretKey(e.target.value)}
                                required
                                className="w-full h-11 px-4 rounded-xl text-sm font-mono outline-none transition-shadow"
                                style={{
                                    backgroundColor: "var(--color-surface-raised)",
                                    border: "1px solid var(--color-border)",
                                    color: "var(--color-text-primary)",
                                    caretColor: "var(--color-accent)",
                                }}
                                onFocus={e => e.currentTarget.style.boxShadow = "0 0 0 2px var(--color-accent-border)"}
                                onBlur={e => e.currentTarget.style.boxShadow = "none"}
                            />
                            <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>{meta.hint}</p>
                        </div>

                        {error && (
                            <div className="flex items-start gap-2 p-3 rounded-xl text-xs font-body" style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#EF4444" }}>
                                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                                {error}
                            </div>
                        )}

                        <div className="flex gap-3 pt-1">
                            <button type="button" onClick={onClose} className="flex-1 h-11 rounded-xl text-sm font-semibold font-body transition-colors"
                                style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>
                                Cancel
                            </button>
                            <button type="submit" disabled={loading} className="flex-1 h-11 rounded-xl text-sm font-bold font-body transition-opacity disabled:opacity-60"
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

interface GatewayCardProps {
    name: string
    description: string
    integration: Integration | undefined
    onConnect: () => void
    available: boolean
}

function GatewayCard({ name, description, integration, onConnect, available }: GatewayCardProps) {
    const connected = integration?.status === "connected"
    const formatDate = (iso: string | null) => {
        if (!iso) return "Never"
        return new Date(iso).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" })
    }

    return (
        <div className={`rounded-2xl p-6 ${!available ? "opacity-50" : ""}`}
            style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold"
                        style={{ backgroundColor: connected ? "rgba(0,201,167,0.1)" : "var(--color-surface-raised)", color: connected ? "var(--color-accent)" : "var(--color-text-muted)", fontFamily: "var(--font-display)" }}>
                        {name[0]}
                    </div>
                    <div>
                        <h3 className="font-bold font-display" style={{ color: "var(--color-text-primary)" }}>{name}</h3>
                        <p className="text-sm font-body" style={{ color: "var(--color-text-muted)" }}>{description}</p>
                    </div>
                </div>
                {connected ? (
                    <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold font-body"
                        style={{ backgroundColor: "var(--color-accent-dim)", color: "var(--color-accent)", border: "1px solid var(--color-accent-border)" }}>
                        <CheckCircle2 className="w-3.5 h-3.5" /> Connected
                    </span>
                ) : available ? (
                    <span className="px-3 py-1 rounded-full text-xs font-semibold font-body"
                        style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>
                        Not connected
                    </span>
                ) : (
                    <span className="px-3 py-1 rounded-full text-xs font-semibold font-body"
                        style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>
                        Coming soon
                    </span>
                )}
            </div>

            {connected && (
                <div className="mt-5 grid grid-cols-2 gap-4">
                    <div className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Last synced</p>
                        <p className="mt-1 text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>
                            {formatDate(integration!.last_sync_at)}
                        </p>
                    </div>
                    <div className="rounded-xl p-4" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Orders imported</p>
                        <p className="mt-1 text-sm font-semibold font-body" style={{ color: "var(--color-text-primary)" }}>
                            {integration!.transaction_count.toLocaleString()}
                        </p>
                    </div>
                </div>
            )}

            {available && (
                <div className="mt-5">
                    {connected ? (
                        <button onClick={onConnect}
                            className="flex items-center gap-2 px-4 h-9 rounded-xl text-sm font-semibold font-body transition-colors"
                            style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>
                            <RefreshCw className="w-3.5 h-3.5" /> Re-connect / Update Key
                        </button>
                    ) : (
                        <button onClick={onConnect}
                            className="flex items-center gap-2 px-5 h-9 rounded-xl text-sm font-bold font-body transition-opacity"
                            style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                            <Plus className="w-4 h-4" /> Connect {name}
                        </button>
                    )}
                </div>
            )}
        </div>
    )
}

export default function IntegrationsPage() {
    const { activeBrandId } = useAuthStore()
    const [integrations, setIntegrations] = useState<Integration[]>([])
    const [modal, setModal] = useState<"paystack" | "flutterwave" | null>(null)

    const load = async () => {
        if (!activeBrandId) return
        try {
            const res = await api.get(`/api/integrations?brand_id=${activeBrandId}`)
            setIntegrations(res.data)
        } catch {
            setIntegrations([])
        }
    }

    useEffect(() => { load() }, [activeBrandId])

    const find = (type: string) => integrations.find(i => i.type === type)

    return (
        <div className="p-8 max-w-3xl space-y-6">
            <div>
                <h1 className="text-2xl font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Integrations</h1>
                <p className="mt-1 text-sm font-body" style={{ color: "var(--color-text-muted)" }}>
                    Connect your payment gateways to automatically import orders and customers.
                </p>
            </div>

            <GatewayCard
                name="Paystack"
                description="Payment gateway — Nigeria, Ghana, South Africa"
                integration={find("paystack")}
                onConnect={() => setModal("paystack")}
                available={true}
            />

            <GatewayCard
                name="Flutterwave"
                description="Payment gateway — Pan-African, 30+ currencies"
                integration={find("flutterwave")}
                onConnect={() => setModal("flutterwave")}
                available={true}
            />

            {["Monnify", "OPay"].map(name => (
                <GatewayCard
                    key={name}
                    name={name}
                    description="Coming soon"
                    integration={undefined}
                    onConnect={() => {}}
                    available={false}
                />
            ))}

            {modal && activeBrandId && (
                <ConnectModal
                    gateway={modal}
                    brandId={activeBrandId}
                    onClose={() => setModal(null)}
                    onSuccess={load}
                />
            )}
        </div>
    )
}
