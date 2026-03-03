"use client"

import { useState, useEffect } from "react"
import { CheckCircle2, XCircle, AlertCircle, Inbox, RefreshCw, ChevronLeft, ChevronRight } from "lucide-react"
import { useAuthStore } from "@/store/auth"
import api from "@/lib/api"

interface InboxOrder {
    id: string
    total_amount: number
    narration: string | null
    ordered_at: string
    status: string
    external_id: string
    payment_gateway: string
    customer_id: string | null
}

interface ConfirmModalProps {
    order: InboxOrder
    onClose: () => void
    onConfirmed: () => void
    brandId: string
}

function ConfirmModal({ order, onClose, onConfirmed, brandId }: ConfirmModalProps) {
    const [customerName, setCustomerName] = useState("")
    const [customerEmail, setCustomerEmail] = useState("")
    const [customerPhone, setCustomerPhone] = useState("")
    const [channel, setChannel] = useState("website")
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")

    const handleConfirm = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true); setError("")
        try {
            await api.post(`/api/orders/${order.id}/confirm`, {
                customer_name: customerName || null,
                customer_email: customerEmail || null,
                customer_phone: customerPhone || null,
                channel,
            })
            onConfirmed()
            onClose()
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Failed to confirm order.")
        } finally { setLoading(false) }
    }

    const inputStyle = {
        backgroundColor: "var(--color-surface-raised)",
        border: "1px solid var(--color-border)",
        color: "var(--color-text-primary)",
        caretColor: "var(--color-accent)",
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ backgroundColor: "rgba(0,0,0,0.6)" }}>
            <div className="w-full max-w-md rounded-2xl p-6 space-y-5" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: "var(--color-accent-dim)" }}>
                        <CheckCircle2 className="w-5 h-5" style={{ color: "var(--color-accent)" }} />
                    </div>
                    <div>
                        <h2 className="text-base font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Confirm as Sale</h2>
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>
                            ₦{order.total_amount.toLocaleString("en-NG")} — {order.narration || "No narration"}
                        </p>
                    </div>
                </div>

                <form onSubmit={handleConfirm} className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                        <div className="col-span-2 space-y-1.5">
                            <label className="block text-xs font-semibold font-body" style={{ color: "var(--color-text-secondary)" }}>
                                Customer Name <span style={{ color: "var(--color-text-muted)" }}>(optional)</span>
                            </label>
                            <input type="text" placeholder="e.g. Amara Johnson" value={customerName}
                                onChange={e => setCustomerName(e.target.value)}
                                className="w-full h-10 px-4 rounded-xl text-sm outline-none font-body"
                                style={inputStyle} />
                        </div>
                        <div className="space-y-1.5">
                            <label className="block text-xs font-semibold font-body" style={{ color: "var(--color-text-secondary)" }}>Email</label>
                            <input type="email" placeholder="customer@email.com" value={customerEmail}
                                onChange={e => setCustomerEmail(e.target.value)}
                                className="w-full h-10 px-4 rounded-xl text-sm outline-none font-body"
                                style={inputStyle} />
                        </div>
                        <div className="space-y-1.5">
                            <label className="block text-xs font-semibold font-body" style={{ color: "var(--color-text-secondary)" }}>Phone</label>
                            <input type="tel" placeholder="080xxxxxxxx" value={customerPhone}
                                onChange={e => setCustomerPhone(e.target.value)}
                                className="w-full h-10 px-4 rounded-xl text-sm outline-none font-body"
                                style={inputStyle} />
                        </div>
                        <div className="col-span-2 space-y-1.5">
                            <label className="block text-xs font-semibold font-body" style={{ color: "var(--color-text-secondary)" }}>Sales Channel</label>
                            <select value={channel} onChange={e => setChannel(e.target.value)}
                                className="w-full h-10 px-4 rounded-xl text-sm outline-none font-body"
                                style={{ ...inputStyle, appearance: "auto" }}>
                                <option value="website">Online / Website</option>
                                <option value="social">Social Media (WhatsApp, IG)</option>
                                <option value="physical">Physical / In-store</option>
                            </select>
                        </div>
                    </div>

                    {error && (
                        <div className="flex items-start gap-2 p-3 rounded-xl text-xs font-body"
                            style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#EF4444" }}>
                            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />{error}
                        </div>
                    )}

                    <div className="flex gap-3 pt-1">
                        <button type="button" onClick={onClose} className="flex-1 h-11 rounded-xl text-sm font-semibold font-body"
                            style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>
                            Cancel
                        </button>
                        <button type="submit" disabled={loading} className="flex-1 h-11 rounded-xl text-sm font-bold font-body disabled:opacity-60"
                            style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                            {loading ? "Confirming..." : "Confirm Sale ✓"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}

// ── Row ───────────────────────────────────────────────────────────────────────

function InboxRow({ order, onConfirm, onArchive }: {
    order: InboxOrder
    onConfirm: () => void
    onArchive: () => void
}) {
    const date = new Date(order.ordered_at).toLocaleDateString("en-NG", { day: "2-digit", month: "short", year: "numeric" })
    const time = new Date(order.ordered_at).toLocaleTimeString("en-NG", { hour: "2-digit", minute: "2-digit" })

    return (
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 rounded-xl transition-colors"
            style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            {/* Date + Amount */}
            <div className="sm:w-44 flex-shrink-0">
                <p className="text-sm font-bold font-body" style={{ color: "var(--color-text-primary)" }}>
                    ₦{order.total_amount.toLocaleString("en-NG", { minimumFractionDigits: 2 })}
                </p>
                <p className="text-xs font-body mt-0.5" style={{ color: "var(--color-text-muted)" }}>{date} · {time}</p>
            </div>

            {/* Narration */}
            <div className="flex-1 min-w-0">
                <p className="text-sm font-body truncate" style={{ color: "var(--color-text-secondary)" }}>
                    {order.narration || <span style={{ color: "var(--color-text-muted)", fontStyle: "italic" }}>No narration</span>}
                </p>
                <p className="text-xs font-body mt-0.5" style={{ color: "var(--color-text-muted)" }}>
                    ref: {order.external_id?.slice(0, 20)}...
                </p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 flex-shrink-0">
                <button onClick={onConfirm}
                    className="flex items-center gap-1.5 px-4 h-8 rounded-lg text-xs font-bold font-body transition-opacity"
                    style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                    <CheckCircle2 className="w-3.5 h-3.5" /> This is a sale
                </button>
                <button onClick={onArchive}
                    className="flex items-center gap-1.5 px-3 h-8 rounded-lg text-xs font-semibold font-body transition-colors"
                    style={{ border: "1px solid var(--color-border)", color: "var(--color-text-muted)", backgroundColor: "transparent" }}>
                    <XCircle className="w-3.5 h-3.5" /> Not a sale
                </button>
            </div>
        </div>
    )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function OrderInboxPage() {
    const { activeBrandId } = useAuthStore()
    const [orders, setOrders] = useState<InboxOrder[]>([])
    const [total, setTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [loading, setLoading] = useState(true)
    const [confirmOrder, setConfirmOrder] = useState<InboxOrder | null>(null)

    const PAGE_SIZE = 20

    const load = async () => {
        if (!activeBrandId) return
        setLoading(true)
        try {
            const res = await api.get(`/api/orders/inbox?brand_id=${activeBrandId}&page=${page}&page_size=${PAGE_SIZE}`)
            setOrders(res.data.orders)
            setTotal(res.data.total)
        } catch { setOrders([]) } finally { setLoading(false) }
    }

    useEffect(() => { load() }, [activeBrandId, page])

    const handleArchive = async (orderId: string) => {
        try {
            await api.post(`/api/orders/${orderId}/archive`, { reason: "Not a sale" })
            load()
        } catch {}
    }

    const totalPages = Math.ceil(total / PAGE_SIZE)

    return (
        <div className="p-8 max-w-4xl">
            {/* Header */}
            <div className="flex items-start justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Order Inbox</h1>
                    <p className="mt-1 text-sm font-body" style={{ color: "var(--color-text-muted)" }}>
                        Bank transfers awaiting your review. Confirm the ones that are sales.
                    </p>
                </div>
                <button onClick={load} className="flex items-center gap-2 px-4 h-9 rounded-xl text-sm font-semibold font-body"
                    style={{ border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", backgroundColor: "transparent" }}>
                    <RefreshCw className="w-3.5 h-3.5" /> Refresh
                </button>
            </div>

            {/* Stats bar */}
            <div className="rounded-xl p-4 mb-6 flex items-center gap-6" style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                <div>
                    <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Pending review</p>
                    <p className="text-xl font-bold font-display" style={{ color: total > 0 ? "#F59E0B" : "var(--color-text-primary)" }}>
                        {total}
                    </p>
                </div>
                <div className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>
                    Each credit in your bank account may or may not be a sale.<br />
                    "This is a sale" → moves it to your Orders. "Not a sale" → archives it.
                </div>
            </div>

            {/* List */}
            {loading ? (
                <div className="space-y-3">
                    {[...Array(5)].map((_, i) => (
                        <div key={i} className="h-20 rounded-xl animate-pulse" style={{ backgroundColor: "var(--color-surface)" }} />
                    ))}
                </div>
            ) : orders.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 gap-4" style={{ color: "var(--color-text-muted)" }}>
                    <Inbox className="w-12 h-12 opacity-30" />
                    <div className="text-center">
                        <p className="font-semibold font-body">All caught up!</p>
                        <p className="text-sm font-body mt-1">No pending bank transfers to review.</p>
                    </div>
                    <a href="/dashboard/integrations" className="text-sm font-semibold font-body" style={{ color: "var(--color-accent)" }}>
                        Connect a bank account →
                    </a>
                </div>
            ) : (
                <div className="space-y-3">
                    {orders.map(order => (
                        <InboxRow
                            key={order.id}
                            order={order}
                            onConfirm={() => setConfirmOrder(order)}
                            onArchive={() => handleArchive(order.id)}
                        />
                    ))}
                </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between mt-6">
                    <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>
                        Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
                    </p>
                    <div className="flex items-center gap-2">
                        <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                            className="w-8 h-8 flex items-center justify-center rounded-lg disabled:opacity-40"
                            style={{ border: "1px solid var(--color-border)", backgroundColor: "transparent", color: "var(--color-text-secondary)" }}>
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        <span className="text-sm font-semibold font-body px-3" style={{ color: "var(--color-text-primary)" }}>
                            {page} / {totalPages}
                        </span>
                        <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                            className="w-8 h-8 flex items-center justify-center rounded-lg disabled:opacity-40"
                            style={{ border: "1px solid var(--color-border)", backgroundColor: "transparent", color: "var(--color-text-secondary)" }}>
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}

            {/* Confirm Modal */}
            {confirmOrder && activeBrandId && (
                <ConfirmModal
                    order={confirmOrder}
                    brandId={activeBrandId}
                    onClose={() => setConfirmOrder(null)}
                    onConfirmed={load}
                />
            )}
        </div>
    )
}
