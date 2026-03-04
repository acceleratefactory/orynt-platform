"use client"

/**
 * ORYNT — Order Inbox
 * Task 1.10: Mobile-first manual order logging for WhatsApp/physical sellers.
 * Target: log a complete order in under 60 seconds.
 *
 * Tabs:
 *   1. "Log New Order"     — WhatsApp parser + manual form
 *   2. "Unmatched Transfers" — pending_match bank transfers
 */

import React, { useCallback, useEffect, useRef, useState } from "react"
import {
    AlertCircle, ArrowLeft, Bot, Check, CheckCircle2, ChevronDown,
    CreditCard, ExternalLink, Inbox, Loader2, MessageSquare, Minus,
    Package, Phone, Plus, Search, Send, ShoppingBag, Sparkles,
    Store, Trash2, User, Wallet, X, Zap,
} from "lucide-react"
import api from "@/lib/api"
import { useAuthStore } from "@/store/auth"
import { cn } from "@/lib/utils"

// ── Types ─────────────────────────────────────────────────────────────────────

interface ProductResult {
    id: string; name: string; sku_code: string | null;
    selling_price: number; current_stock: number; is_digital: boolean
}
interface CustomerResult {
    id: string; name: string | null; email: string; phone: string | null
}
interface OrderItem {
    product_id: string | null; product_name: string
    quantity: number; unit_price: number
}
interface Transfer {
    id: string; total_amount: number; narration: string | null
    ordered_at: string; payment_gateway: string | null
}

// ── Payment method config ─────────────────────────────────────────────────────

const PAYMENT_METHODS = [
    { value: "cash", label: "Cash", icon: Wallet, color: "#22c55e" },
    { value: "bank_transfer", label: "Bank Transfer", icon: CreditCard, color: "#3b82f6" },
    { value: "opay", label: "OPay", icon: Zap, color: "#16a34a" },
    { value: "palmpay", label: "PalmPay", icon: Send, color: "#f97316" },
    { value: "paystack", label: "Paystack", icon: CreditCard, color: "#00c9a7" },
    { value: "whatsapp_pay", label: "WhatsApp Pay", icon: MessageSquare, color: "#25d366" },
]

const CHANNELS = [
    { value: "whatsapp", label: "WhatsApp", icon: MessageSquare },
    { value: "instagram", label: "Instagram", icon: ExternalLink },
    { value: "in_person", label: "In Person", icon: Store },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (n: number) =>
    "₦" + n.toLocaleString("en-NG", { minimumFractionDigits: 0, maximumFractionDigits: 0 })

const fmtDate = (iso: string) =>
    new Date(iso).toLocaleString("en-NG", { dateStyle: "medium", timeStyle: "short" })

function useDebounce<T>(val: T, ms = 350): T {
    const [deb, setDeb] = useState(val)
    useEffect(() => {
        const t = setTimeout(() => setDeb(val), ms)
        return () => clearTimeout(t)
    }, [val, ms])
    return deb
}

// ── CustomerSearch ───────────────────────────────────────────────────────────

function CustomerSearch({
    brandId, onSelect, value, onChange, name, onNameChange
}: {
    brandId: string
    onSelect: (c: CustomerResult) => void
    value: string; onChange: (v: string) => void
    name: string; onNameChange: (v: string) => void
}) {
    const [results, setResults] = useState<CustomerResult[]>([])
    const [open, setOpen] = useState(false)
    const debQuery = useDebounce(value, 300)

    useEffect(() => {
        if (debQuery.replace(/\D/g, "").length < 3 && debQuery.length < 3) {
            setResults([]); setOpen(false); return
        }
        api.get("/api/orders/customers/search", { params: { brand_id: brandId, q: debQuery } })
            .then(r => { setResults(r.data.customers); setOpen(r.data.customers.length > 0) })
            .catch(() => { setResults([]); setOpen(false) })
    }, [debQuery, brandId])

    return (
        <div className="relative">
            <div className="relative">
                <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--color-text-muted)" }} />
                <input
                    id="customer-phone"
                    type="tel" inputMode="tel" autoComplete="tel"
                    placeholder="Customer phone (e.g. 08012345678)"
                    value={value}
                    onChange={e => onChange(e.target.value)}
                    className="w-full h-14 pl-12 pr-4 rounded-2xl text-base outline-none font-body"
                    style={{
                        backgroundColor: "var(--color-surface-raised)",
                        border: "1.5px solid var(--color-border)",
                        color: "var(--color-text-primary)", fontSize: "16px"
                    }}
                    onFocus={e => (e.currentTarget.style.borderColor = "var(--color-accent)")}
                    onBlur={e => { e.currentTarget.style.borderColor = "var(--color-border)"; setTimeout(() => setOpen(false), 150) }}
                />
            </div>
            {open && (
                <div className="absolute z-20 left-0 right-0 mt-1 rounded-2xl overflow-hidden shadow-xl"
                    style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                    {results.map(c => (
                        <button key={c.id} type="button"
                            className="w-full flex items-center gap-3 p-4 hover:bg-white/5 text-left"
                            onClick={() => { onSelect(c); setOpen(false) }}>
                            <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                                style={{ backgroundColor: "var(--color-accent-dim)" }}>
                                <User className="w-4 h-4" style={{ color: "var(--color-accent)" }} />
                            </div>
                            <div>
                                <p className="font-semibold text-sm font-body" style={{ color: "var(--color-text-primary)" }}>{c.name || "(no name)"}</p>
                                <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>{c.phone || c.email}</p>
                            </div>
                        </button>
                    ))}
                </div>
            )}
            <div className="mt-3 relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--color-text-muted)" }} />
                <input
                    id="customer-name"
                    type="text" autoComplete="name"
                    placeholder="Customer name"
                    value={name}
                    onChange={e => onNameChange(e.target.value)}
                    className="w-full h-14 pl-12 pr-4 rounded-2xl text-base outline-none font-body"
                    style={{
                        backgroundColor: "var(--color-surface-raised)",
                        border: "1.5px solid var(--color-border)",
                        color: "var(--color-text-primary)", fontSize: "16px"
                    }}
                    onFocus={e => (e.currentTarget.style.borderColor = "var(--color-accent)")}
                    onBlur={e => (e.currentTarget.style.borderColor = "var(--color-border)")}
                />
            </div>
        </div>
    )
}

// ── ProductPicker ─────────────────────────────────────────────────────────────

function ProductPicker({
    brandId, items, onAdd, onRemove, onQtyChange, onPriceChange
}: {
    brandId: string
    items: OrderItem[]
    onAdd: (p: ProductResult) => void
    onRemove: (i: number) => void
    onQtyChange: (i: number, qty: number) => void
    onPriceChange: (i: number, price: number) => void
}) {
    const [search, setSearch] = useState("")
    const [results, setResults] = useState<ProductResult[]>([])
    const [open, setOpen] = useState(false)
    const [loading, setLoading] = useState(false)
    const debSearch = useDebounce(search, 300)

    useEffect(() => {
        setLoading(true)
        api.get("/api/orders/products/search", { params: { brand_id: brandId, q: debSearch } })
            .then(r => { setResults(r.data.products); setOpen(true) })
            .catch(() => setResults([]))
            .finally(() => setLoading(false))
    }, [debSearch, brandId])

    const addedIds = new Set(items.map(i => i.product_id).filter(Boolean))

    return (
        <div className="space-y-3">
            {/* Added items */}
            {items.map((item, idx) => (
                <div key={idx} className="rounded-2xl p-4 space-y-3"
                    style={{ backgroundColor: "var(--color-surface-raised)", border: "1px solid var(--color-border)" }}>
                    <div className="flex items-center justify-between gap-2">
                        <p className="font-semibold text-sm font-body flex-1 truncate" style={{ color: "var(--color-text-primary)" }}>
                            {item.product_name}
                        </p>
                        <button type="button" onClick={() => onRemove(idx)}
                            className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
                            style={{ backgroundColor: "rgba(239,68,68,0.1)", color: "#EF4444" }}>
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        {/* Quantity */}
                        <div className="space-y-1">
                            <label className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Quantity</label>
                            <div className="flex items-center h-12 rounded-xl overflow-hidden"
                                style={{ border: "1.5px solid var(--color-border)", backgroundColor: "var(--color-surface)" }}>
                                <button type="button"
                                    className="w-12 h-full flex items-center justify-center"
                                    style={{ color: "var(--color-text-muted)" }}
                                    onClick={() => onQtyChange(idx, Math.max(1, item.quantity - 1))}>
                                    <Minus className="w-4 h-4" />
                                </button>
                                <span className="flex-1 text-center font-bold font-body" style={{ color: "var(--color-text-primary)" }}>
                                    {item.quantity}
                                </span>
                                <button type="button"
                                    className="w-12 h-full flex items-center justify-center"
                                    style={{ color: "var(--color-accent)" }}
                                    onClick={() => onQtyChange(idx, item.quantity + 1)}>
                                    <Plus className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                        {/* Price */}
                        <div className="space-y-1">
                            <label className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Unit Price (₦)</label>
                            <input
                                type="number" inputMode="numeric"
                                value={item.unit_price}
                                onChange={e => onPriceChange(idx, parseFloat(e.target.value) || 0)}
                                className="w-full h-12 px-3 rounded-xl text-base font-body outline-none"
                                style={{
                                    border: "1.5px solid var(--color-border)",
                                    backgroundColor: "var(--color-surface)",
                                    color: "var(--color-text-primary)", fontSize: "16px"
                                }}
                                onFocus={e => (e.currentTarget.style.borderColor = "var(--color-accent)")}
                                onBlur={e => (e.currentTarget.style.borderColor = "var(--color-border)")}
                            />
                        </div>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>Line total</span>
                        <span className="font-bold font-body" style={{ color: "var(--color-accent)" }}>
                            {fmt(item.unit_price * item.quantity)}
                        </span>
                    </div>
                </div>
            ))}

            {/* Search */}
            <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--color-text-muted)" }} />
                <input
                    type="text" placeholder="Search or type product name..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="w-full h-14 pl-12 pr-4 rounded-2xl text-base outline-none font-body"
                    style={{
                        backgroundColor: "var(--color-surface-raised)",
                        border: "1.5px solid var(--color-border)",
                        color: "var(--color-text-primary)", fontSize: "16px"
                    }}
                    onFocus={e => { e.currentTarget.style.borderColor = "var(--color-accent)"; setOpen(true) }}
                    onBlur={e => { e.currentTarget.style.borderColor = "var(--color-border)"; setTimeout(() => setOpen(false), 200) }}
                />
            </div>

            {open && results.length > 0 && (
                <div className="rounded-2xl overflow-hidden shadow-xl"
                    style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                    {results.filter(r => !addedIds.has(r.id)).map(p => (
                        <button key={p.id} type="button"
                            className="w-full flex items-center gap-3 p-4 hover:bg-white/5 text-left border-b last:border-0"
                            style={{ borderColor: "var(--color-border)" }}
                            onClick={() => { onAdd(p); setSearch(""); setOpen(false) }}>
                            <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                                style={{ backgroundColor: "var(--color-surface-raised)" }}>
                                <Package className="w-4 h-4" style={{ color: "var(--color-text-muted)" }} />
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="font-semibold text-sm font-body truncate" style={{ color: "var(--color-text-primary)" }}>{p.name}</p>
                                <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>
                                    {fmt(p.selling_price)} {p.sku_code && `· ${p.sku_code}`}
                                </p>
                            </div>
                            <Plus className="w-5 h-5 flex-shrink-0" style={{ color: "var(--color-accent)" }} />
                        </button>
                    ))}
                    {/* Add as free-text item */}
                    {search.trim() && (
                        <button type="button"
                            className="w-full flex items-center gap-3 p-4 hover:bg-white/5 text-left"
                            onClick={() => {
                                onAdd({ id: "", name: search.trim(), sku_code: null, selling_price: 0, current_stock: 0, is_digital: false })
                                setSearch(""); setOpen(false)
                            }}>
                            <Plus className="w-5 h-5" style={{ color: "var(--color-accent)" }} />
                            <span className="text-sm font-body" style={{ color: "var(--color-text-secondary)" }}>
                                Add "{search.trim()}" as custom item
                            </span>
                        </button>
                    )}
                </div>
            )}
        </div>
    )
}

// ── WhatsApp Parser Panel ─────────────────────────────────────────────────────

interface ParsedData {
    customer_name?: string | null
    customer_phone?: string | null
    delivery_address?: string | null
    items?: { product_name: string; quantity: number; unit_price: number | null }[]
    total_amount?: number | null
    note?: string | null
}

function WhatsAppParser({
    brandId,
    onParsed,
    onClose
}: { brandId: string; onParsed: (d: ParsedData) => void; onClose: () => void }) {
    const [msg, setMsg] = useState("")
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")

    const handleParse = async () => {
        if (!msg.trim()) return
        setLoading(true); setError("")
        try {
            const r = await api.post("/api/orders/parse-whatsapp", { message: msg, brand_id: brandId })
            if (r.data.parsed) {
                onParsed(r.data)
            } else {
                setError(r.data.reason || "Could not parse — please fill manually.")
            }
        } catch (e: any) {
            setError(e?.response?.data?.detail || "Parsing failed. Please fill the form manually.")
        } finally { setLoading(false) }
    }

    return (
        <div className="rounded-2xl overflow-hidden"
            style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="flex items-center justify-between p-4"
                style={{ borderBottom: "1px solid var(--color-border)", backgroundColor: "var(--color-surface-raised)" }}>
                <div className="flex items-center gap-2">
                    <Bot className="w-5 h-5" style={{ color: "var(--color-accent)" }} />
                    <span className="font-bold text-sm font-body" style={{ color: "var(--color-text-primary)" }}>
                        Parse WhatsApp Message
                    </span>
                </div>
                <button type="button" onClick={onClose}
                    className="w-8 h-8 rounded-xl flex items-center justify-center"
                    style={{ color: "var(--color-text-muted)", backgroundColor: "var(--color-surface)" }}>
                    <X className="w-4 h-4" />
                </button>
            </div>
            <div className="p-4 space-y-3">
                <textarea
                    placeholder={"Paste the customer's WhatsApp message here...\n\nExample: Hi, I want to order 2 Ankara bags at 5500 each. My name is Amina. Delivery to Lekki phase 1. I'll pay via transfer."}
                    value={msg}
                    onChange={e => setMsg(e.target.value)}
                    rows={5}
                    className="w-full p-4 rounded-2xl text-sm font-body outline-none resize-none"
                    style={{
                        backgroundColor: "var(--color-surface-raised)",
                        border: "1.5px solid var(--color-border)",
                        color: "var(--color-text-primary)", fontSize: "16px", lineHeight: "1.6"
                    }}
                    onFocus={e => (e.currentTarget.style.borderColor = "var(--color-accent)")}
                    onBlur={e => (e.currentTarget.style.borderColor = "var(--color-border)")}
                />
                {error && (
                    <div className="flex items-start gap-2 p-3 rounded-xl text-sm font-body"
                        style={{ backgroundColor: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.2)", color: "#FBB124" }}>
                        <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />{error}
                    </div>
                )}
                <button type="button" onClick={handleParse} disabled={loading || !msg.trim()}
                    className="w-full h-14 rounded-2xl font-bold text-base font-body disabled:opacity-50 flex items-center justify-center gap-2"
                    style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                    {loading ? <><Loader2 className="w-5 h-5 animate-spin" /> Extracting...</>
                        : <><Sparkles className="w-5 h-5" /> Extract Order Details</>}
                </button>
                <p className="text-xs text-center font-body" style={{ color: "var(--color-text-muted)" }}>
                    AI will extract details — you review before submitting
                </p>
            </div>
        </div>
    )
}

// ── LOG ORDER FORM ────────────────────────────────────────────────────────────

function LogOrderForm({ brandId }: { brandId: string }) {
    const [phone, setPhone] = useState("")
    const [customerName, setCustomerName] = useState("")
    const [items, setItems] = useState<OrderItem[]>([])
    const [paymentMethod, setPaymentMethod] = useState("cash")
    const [channel, setChannel] = useState("whatsapp")
    const [deliveryAddress, setDeliveryAddress] = useState("")
    const [note, setNote] = useState("")
    const [showParser, setShowParser] = useState(false)
    const [loading, setLoading] = useState(false)
    const [success, setSuccess] = useState<{ id: string; total: number } | null>(null)
    const [error, setError] = useState("")

    const autoTotal = items.reduce((s, i) => s + i.unit_price * i.quantity, 0)

    const addProduct = (p: ProductResult) => {
        setItems(prev => [...prev, {
            product_id: p.id || null,
            product_name: p.name,
            quantity: 1,
            unit_price: p.selling_price || 0,
        }])
    }

    const handleParsed = (d: ParsedData) => {
        setShowParser(false)
        if (d.customer_name) setCustomerName(d.customer_name)
        if (d.customer_phone) setPhone(d.customer_phone)
        if (d.delivery_address) setDeliveryAddress(d.delivery_address)
        if (d.note) setNote(d.note)
        if (d.items && d.items.length > 0) {
            setItems(d.items.map(i => ({
                product_id: null,
                product_name: i.product_name,
                quantity: i.quantity || 1,
                unit_price: i.unit_price || 0,
            })))
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (items.length === 0) { setError("Add at least one product."); return }
        if (autoTotal <= 0) { setError("Total amount must be greater than zero."); return }
        setLoading(true); setError("")
        try {
            const r = await api.post("/api/orders/manual", {
                brand_id: brandId,
                customer_phone: phone || null,
                customer_name: customerName || null,
                items,
                total_amount: autoTotal,
                payment_method: paymentMethod,
                channel,
                delivery_address: deliveryAddress || null,
                note: note || null,
            })
            setSuccess({ id: r.data.order.id, total: r.data.order.total_amount })
        } catch (e: any) {
            setError(e?.response?.data?.detail || "Failed to log order. Try again.")
        } finally { setLoading(false) }
    }

    const resetForm = () => {
        setPhone(""); setCustomerName(""); setItems([])
        setPaymentMethod("cash"); setChannel("whatsapp")
        setDeliveryAddress(""); setNote(""); setSuccess(null); setError("")
    }

    if (success) {
        return (
            <div className="flex flex-col items-center justify-center py-16 px-6 text-center space-y-4">
                <div className="w-20 h-20 rounded-full flex items-center justify-center"
                    style={{ backgroundColor: "var(--color-accent-dim)" }}>
                    <CheckCircle2 className="w-10 h-10" style={{ color: "var(--color-accent)" }} />
                </div>
                <h2 className="text-2xl font-bold font-display" style={{ color: "var(--color-text-primary)" }}>Order Logged!</h2>
                <p className="font-body" style={{ color: "var(--color-text-muted)" }}>
                    {fmt(success.total)} recorded successfully.
                </p>
                <p className="text-xs font-body font-mono" style={{ color: "var(--color-text-muted)" }}>
                    #{success.id.slice(-8).toUpperCase()}
                </p>
                <button onClick={resetForm}
                    className="mt-4 w-full max-w-xs h-14 rounded-2xl font-bold font-body text-base"
                    style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                    Log Another Order
                </button>
            </div>
        )
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-6 pb-24">
            {/* WhatsApp parser toggle */}
            {!showParser ? (
                <button type="button" onClick={() => setShowParser(true)}
                    className="w-full h-12 rounded-2xl flex items-center justify-center gap-2 font-semibold text-sm font-body"
                    style={{ border: "1.5px dashed var(--color-accent-border)", color: "var(--color-accent)", backgroundColor: "var(--color-accent-dim)" }}>
                    <Bot className="w-4 h-4" />
                    Paste WhatsApp message → auto-fill form
                </button>
            ) : (
                <WhatsAppParser brandId={brandId} onParsed={handleParsed} onClose={() => setShowParser(false)} />
            )}

            {/* Section: Customer */}
            <div className="space-y-2">
                <SectionLabel icon={User} label="Customer" />
                <CustomerSearch
                    brandId={brandId}
                    value={phone} onChange={setPhone}
                    name={customerName} onNameChange={setCustomerName}
                    onSelect={c => {
                        setPhone(c.phone || "")
                        setCustomerName(c.name || "")
                    }}
                />
            </div>

            {/* Section: Products */}
            <div className="space-y-2">
                <SectionLabel icon={ShoppingBag} label="Products" />
                <ProductPicker
                    brandId={brandId} items={items}
                    onAdd={addProduct}
                    onRemove={i => setItems(prev => prev.filter((_, idx) => idx !== i))}
                    onQtyChange={(i, qty) => setItems(prev => prev.map((item, idx) => idx === i ? { ...item, quantity: qty } : item))}
                    onPriceChange={(i, price) => setItems(prev => prev.map((item, idx) => idx === i ? { ...item, unit_price: price } : item))}
                />
                {/* Total display */}
                {items.length > 0 && (
                    <div className="flex items-center justify-between px-4 py-3 rounded-2xl"
                        style={{ backgroundColor: "var(--color-accent-dim)", border: "1px solid var(--color-accent-border)" }}>
                        <span className="font-body text-sm" style={{ color: "var(--color-text-secondary)" }}>Order Total</span>
                        <span className="text-2xl font-bold font-display" style={{ color: "var(--color-accent)" }}>
                            {fmt(autoTotal)}
                        </span>
                    </div>
                )}
            </div>

            {/* Section: Payment Method */}
            <div className="space-y-2">
                <SectionLabel icon={Wallet} label="Payment Method" />
                <div className="grid grid-cols-3 gap-2">
                    {PAYMENT_METHODS.map(m => {
                        const Icon = m.icon
                        const sel = paymentMethod === m.value
                        return (
                            <button key={m.value} type="button"
                                onClick={() => setPaymentMethod(m.value)}
                                className="h-16 rounded-2xl flex flex-col items-center justify-center gap-1 transition-all"
                                style={{
                                    backgroundColor: sel ? `${m.color}18` : "var(--color-surface-raised)",
                                    border: sel ? `2px solid ${m.color}` : "1.5px solid var(--color-border)",
                                }}>
                                <Icon className="w-5 h-5" style={{ color: sel ? m.color : "var(--color-text-muted)" }} />
                                <span className="text-xs font-semibold font-body leading-tight text-center"
                                    style={{ color: sel ? m.color : "var(--color-text-secondary)" }}>
                                    {m.label}
                                </span>
                            </button>
                        )
                    })}
                </div>
            </div>

            {/* Section: Channel */}
            <div className="space-y-2">
                <SectionLabel icon={MessageSquare} label="Channel" />
                <div className="grid grid-cols-3 gap-2">
                    {CHANNELS.map(c => {
                        const Icon = c.icon
                        const sel = channel === c.value
                        return (
                            <button key={c.value} type="button"
                                onClick={() => setChannel(c.value)}
                                className="h-14 rounded-2xl flex items-center justify-center gap-2 transition-all font-body text-sm font-semibold"
                                style={{
                                    backgroundColor: sel ? "var(--color-accent-dim)" : "var(--color-surface-raised)",
                                    border: sel ? "2px solid var(--color-accent)" : "1.5px solid var(--color-border)",
                                    color: sel ? "var(--color-accent)" : "var(--color-text-secondary)"
                                }}>
                                <Icon className="w-4 h-4" />{c.label}
                            </button>
                        )
                    })}
                </div>
            </div>

            {/* Section: Delivery & Note */}
            <div className="space-y-3">
                <SectionLabel icon={Send} label="Delivery & Notes (optional)" />
                <textarea
                    placeholder="Delivery address (estate, street, city...)"
                    value={deliveryAddress}
                    onChange={e => setDeliveryAddress(e.target.value)}
                    rows={2}
                    className="w-full p-4 rounded-2xl text-sm font-body outline-none resize-none"
                    style={{
                        backgroundColor: "var(--color-surface-raised)",
                        border: "1.5px solid var(--color-border)",
                        color: "var(--color-text-primary)", fontSize: "16px"
                    }}
                    onFocus={e => (e.currentTarget.style.borderColor = "var(--color-accent)")}
                    onBlur={e => (e.currentTarget.style.borderColor = "var(--color-border)")}
                />
                <textarea
                    placeholder="Note (optional)"
                    value={note}
                    onChange={e => setNote(e.target.value)}
                    rows={2}
                    className="w-full p-4 rounded-2xl text-sm font-body outline-none resize-none"
                    style={{
                        backgroundColor: "var(--color-surface-raised)",
                        border: "1.5px solid var(--color-border)",
                        color: "var(--color-text-primary)", fontSize: "16px"
                    }}
                    onFocus={e => (e.currentTarget.style.borderColor = "var(--color-accent)")}
                    onBlur={e => (e.currentTarget.style.borderColor = "var(--color-border)")}
                />
            </div>

            {error && (
                <div className="flex items-start gap-2 p-4 rounded-2xl text-sm font-body"
                    style={{ backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#EF4444" }}>
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />{error}
                </div>
            )}

            {/* Submit */}
            <div className="fixed bottom-0 left-0 right-0 p-4 max-w-2xl mx-auto"
                style={{ backgroundColor: "var(--color-background)", borderTop: "1px solid var(--color-border)" }}>
                <button type="submit" disabled={loading || items.length === 0}
                    className="w-full h-16 rounded-2xl font-bold text-lg font-body disabled:opacity-50 flex items-center justify-center gap-2"
                    style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                    {loading ? <><Loader2 className="w-5 h-5 animate-spin" /> Saving...</>
                        : <><Check className="w-5 h-5" /> Log Order {items.length > 0 && `· ${fmt(autoTotal)}`}</>}
                </button>
            </div>
        </form>
    )
}

// ── UNMATCHED TRANSFERS TAB ───────────────────────────────────────────────────

function ConfirmTransferDialog({
    order, brandId, onDone, onClose
}: { order: Transfer; brandId: string; onDone: () => void; onClose: () => void }) {
    const [phone, setPhone] = useState("")
    const [name, setName] = useState("")
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")

    const handleConfirm = async () => {
        setLoading(true); setError("")
        try {
            await api.post(`/api/orders/${order.id}/confirm-transfer`, {
                customer_phone: phone || null,
                customer_name: name || null,
                channel: "website",
            })
            onDone()
        } catch (e: any) {
            setError(e?.response?.data?.detail || "Failed to confirm. Try again.")
        } finally { setLoading(false) }
    }

    const handleArchive = async () => {
        setLoading(true)
        try {
            await api.post(`/api/orders/${order.id}/archive`, { reason: "Not a sale" })
            onDone()
        } catch { setLoading(false) }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4"
            style={{ backgroundColor: "rgba(0,0,0,0.6)" }}
            onClick={e => { if (e.target === e.currentTarget) onClose() }}>
            <div className="w-full max-w-sm rounded-3xl overflow-hidden"
                style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                <div className="p-5"
                    style={{ borderBottom: "1px solid var(--color-border)", backgroundColor: "var(--color-surface-raised)" }}>
                    <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>
                        {fmtDate(order.ordered_at)}
                    </p>
                    <p className="text-2xl font-bold font-display mt-1" style={{ color: "var(--color-accent)" }}>
                        {fmt(order.total_amount)}
                    </p>
                    {order.narration && (
                        <p className="text-xs mt-1 font-body" style={{ color: "var(--color-text-muted)" }}>
                            {order.narration}
                        </p>
                    )}
                </div>
                <div className="p-5 space-y-3">
                    <p className="text-sm font-semibold font-body" style={{ color: "var(--color-text-secondary)" }}>Who sent this?</p>
                    <div className="relative">
                        <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--color-text-muted)" }} />
                        <input type="tel" placeholder="Customer phone (optional)" value={phone}
                            onChange={e => setPhone(e.target.value)}
                            className="w-full h-12 pl-12 pr-4 rounded-2xl text-sm font-body outline-none"
                            style={{ backgroundColor: "var(--color-surface-raised)", border: "1.5px solid var(--color-border)", color: "var(--color-text-primary)", fontSize: "16px" }}
                            onFocus={e => (e.currentTarget.style.borderColor = "var(--color-accent)")}
                            onBlur={e => (e.currentTarget.style.borderColor = "var(--color-border)")} />
                    </div>
                    <div className="relative">
                        <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--color-text-muted)" }} />
                        <input type="text" placeholder="Customer name (optional)" value={name}
                            onChange={e => setName(e.target.value)}
                            className="w-full h-12 pl-12 pr-4 rounded-2xl text-sm font-body outline-none"
                            style={{ backgroundColor: "var(--color-surface-raised)", border: "1.5px solid var(--color-border)", color: "var(--color-text-primary)", fontSize: "16px" }}
                            onFocus={e => (e.currentTarget.style.borderColor = "var(--color-accent)")}
                            onBlur={e => (e.currentTarget.style.borderColor = "var(--color-border)")} />
                    </div>
                    {error && (
                        <p className="text-xs font-body" style={{ color: "#EF4444" }}>{error}</p>
                    )}
                    <div className="grid grid-cols-2 gap-3 pt-2">
                        <button onClick={handleArchive} disabled={loading}
                            className="h-12 rounded-2xl text-sm font-semibold font-body"
                            style={{ border: "1.5px solid var(--color-border)", color: "var(--color-text-muted)", backgroundColor: "transparent" }}>
                            Not a sale
                        </button>
                        <button onClick={handleConfirm} disabled={loading}
                            className="h-12 rounded-2xl text-sm font-bold font-body disabled:opacity-50 flex items-center justify-center gap-2"
                            style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                            Confirm Sale
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

function UnmatchedTransfersTab({ brandId, transfers, onRefresh }: {
    brandId: string; transfers: Transfer[]; onRefresh: () => void
}) {
    const [selected, setSelected] = useState<Transfer | null>(null)

    if (transfers.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-20 text-center px-6">
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
                    style={{ backgroundColor: "var(--color-surface-raised)" }}>
                    <CheckCircle2 className="w-8 h-8" style={{ color: "var(--color-accent)" }} />
                </div>
                <p className="font-bold font-display text-lg" style={{ color: "var(--color-text-primary)" }}>
                    All clear!
                </p>
                <p className="text-sm font-body mt-1" style={{ color: "var(--color-text-muted)" }}>
                    No unmatched bank transfers right now.
                </p>
            </div>
        )
    }

    return (
        <div className="space-y-3">
            <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>
                {transfers.length} transfer{transfers.length !== 1 ? "s" : ""} awaiting confirmation
            </p>
            {transfers.map(t => (
                <div key={t.id} className="rounded-2xl p-4"
                    style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                    <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                            <p className="font-bold font-body text-lg" style={{ color: "var(--color-text-primary)" }}>
                                {fmt(t.total_amount)}
                            </p>
                            {t.narration && (
                                <p className="text-sm font-body mt-0.5 truncate" style={{ color: "var(--color-text-muted)" }}>
                                    {t.narration}
                                </p>
                            )}
                            <p className="text-xs font-body mt-1" style={{ color: "var(--color-text-muted)" }}>
                                {fmtDate(t.ordered_at)}
                            </p>
                        </div>
                        <button onClick={() => setSelected(t)}
                            className="flex-shrink-0 h-10 px-5 rounded-2xl font-bold text-sm font-body"
                            style={{ backgroundColor: "var(--color-accent)", color: "#0A0A0F" }}>
                            Confirm Sale
                        </button>
                    </div>
                </div>
            ))}

            {selected && (
                <ConfirmTransferDialog
                    order={selected} brandId={brandId}
                    onDone={() => { setSelected(null); onRefresh() }}
                    onClose={() => setSelected(null)}
                />
            )}
        </div>
    )
}

// ── Section label helper ──────────────────────────────────────────────────────

function SectionLabel({ icon: Icon, label }: { icon: React.ElementType; label: string }) {
    return (
        <div className="flex items-center gap-2 mb-1">
            <Icon className="w-4 h-4" style={{ color: "var(--color-text-muted)" }} />
            <span className="text-xs font-bold uppercase tracking-widest font-body" style={{ color: "var(--color-text-muted)" }}>
                {label}
            </span>
        </div>
    )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function InboxPage() {
    const { activeBrandId } = useAuthStore()
    const [tab, setTab] = useState<"log" | "transfers">("log")
    const [transfers, setTransfers] = useState<Transfer[]>([])
    const [unmatched, setUnmatched] = useState(0)
    const [loadingInbox, setLoadingInbox] = useState(false)

    const loadInbox = useCallback(async () => {
        if (!activeBrandId) return
        setLoadingInbox(true)
        try {
            const r = await api.get("/api/orders/inbox", { params: { brand_id: activeBrandId } })
            setTransfers(r.data.unmatched_transfers || [])
            setUnmatched(r.data.unmatched_count || 0)
        } catch { }
        finally { setLoadingInbox(false) }
    }, [activeBrandId])

    useEffect(() => { loadInbox() }, [loadInbox])

    if (!activeBrandId) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <p className="font-body" style={{ color: "var(--color-text-muted)" }}>Select a brand to use the Order Inbox.</p>
            </div>
        )
    }

    return (
        <div className="min-h-screen max-w-2xl mx-auto" style={{ backgroundColor: "var(--color-background)" }}>
            {/* Header */}
            <div className="sticky top-0 z-30 px-4 pt-6 pb-3"
                style={{ backgroundColor: "var(--color-background)", borderBottom: "1px solid var(--color-border)" }}>
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
                        style={{ backgroundColor: "var(--color-accent-dim)" }}>
                        <Inbox className="w-5 h-5" style={{ color: "var(--color-accent)" }} />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold font-display" style={{ color: "var(--color-text-primary)" }}>
                            Order Inbox
                        </h1>
                        <p className="text-xs font-body" style={{ color: "var(--color-text-muted)" }}>
                            Log orders in under 60 seconds
                        </p>
                    </div>
                </div>
                {/* Tabs */}
                <div className="flex gap-1 p-1 rounded-2xl" style={{ backgroundColor: "var(--color-surface-raised)" }}>
                    {[
                        { id: "log", label: "Log New Order" },
                        { id: "transfers", label: "Unmatched Transfers", badge: unmatched > 0 ? unmatched : undefined },
                    ].map(t => (
                        <button key={t.id} onClick={() => setTab(t.id as typeof tab)}
                            className="flex-1 h-10 rounded-xl text-sm font-bold font-body flex items-center justify-center gap-2 transition-all"
                            style={tab === t.id
                                ? { backgroundColor: "var(--color-accent)", color: "#0A0A0F" }
                                : { color: "var(--color-text-muted)", backgroundColor: "transparent" }}>
                            {t.label}
                            {t.badge !== undefined && (
                                <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold"
                                    style={{ backgroundColor: tab === t.id ? "rgba(0,0,0,0.2)" : "rgba(239,68,68,0.8)", color: "#fff" }}>
                                    {t.badge}
                                </span>
                            )}
                        </button>
                    ))}
                </div>
            </div>

            {/* Content */}
            <div className="px-4 pt-6">
                {tab === "log" ? (
                    <LogOrderForm brandId={activeBrandId} />
                ) : (
                    <UnmatchedTransfersTab
                        brandId={activeBrandId}
                        transfers={transfers}
                        onRefresh={loadInbox}
                    />
                )}
            </div>
        </div>
    )
}
