"use client"

import { useState, useRef } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/store/auth"
import { cn } from "@/lib/utils"
import api from "@/lib/api"
import {
    Globe, MessageCircle, Store, BookOpen,
    Upload, Plus, Trash2, ArrowRight, ArrowLeft,
    CheckCircle2, SkipForward
} from "lucide-react"

interface OnboardingFlowProps {
    brandId: string
    brandName: string
    onComplete: () => void
}

// Step 1 options
const SELLER_TYPES = [
    { value: "website", label: "I have a website", sub: "Shopify / WooCommerce / Bumpa", icon: Globe },
    { value: "social_whatsapp", label: "I sell on social media & WhatsApp", sub: "Instagram, TikTok, WhatsApp DMs", icon: MessageCircle },
    { value: "physical", label: "I have a physical shop or kiosk", sub: "Walk-in customers, market stall", icon: Store },
    { value: "digital", label: "I sell digital products", sub: "Ebooks, courses, templates, software", icon: BookOpen },
]

// Step 2 options
const PAYMENT_METHODS = [
    { value: "paystack", label: "Paystack" },
    { value: "flutterwave", label: "Flutterwave" },
    { value: "monnify", label: "Monnify (Moniepoint)" },
    { value: "opay", label: "OPay" },
    { value: "bank_transfer", label: "Bank Transfer" },
    { value: "cash", label: "Cash" },
]

interface ProductRow {
    name: string
    selling_price: string
    cost_price: string
    current_stock: string
    sku_code: string
}

const emptyProduct = (): ProductRow => ({
    name: "", selling_price: "", cost_price: "", current_stock: "0", sku_code: ""
})

export function OnboardingFlow({ brandId, brandName, onComplete }: OnboardingFlowProps) {
    const router = useRouter()
    const [step, setStep] = useState(1)
    const [sellerType, setSellerType] = useState("")
    const [paymentMethods, setPaymentMethods] = useState<string[]>([])
    const [products, setProducts] = useState<ProductRow[]>([emptyProduct()])
    const [csvFile, setCsvFile] = useState<File | null>(null)
    const [csvMode, setCsvMode] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")
    const fileRef = useRef<HTMLInputElement>(null)

    const isDigital = sellerType === "digital"
    const needsProductCatalog = sellerType !== "website" // Step 3 shown for B, C, D

    const totalSteps = needsProductCatalog ? 4 : 3

    // ── Step 1 → 2 ───────────────────────────────────────────────────────────
    const handleStep1Next = async () => {
        if (!sellerType) return
        setLoading(true)
        try {
            await api.patch(`/api/brands/${brandId}`, { seller_type: sellerType })
            setStep(2)
        } catch {
            setError("Failed to save. Please try again.")
        } finally {
            setLoading(false)
        }
    }

    // ── Step 2 → 3 ───────────────────────────────────────────────────────────
    const handleStep2Next = async () => {
        if (paymentMethods.length === 0) return
        setLoading(true)
        try {
            await api.patch(`/api/brands/${brandId}`, { payment_methods: paymentMethods })
            setStep(needsProductCatalog ? 3 : 4)
        } catch {
            setError("Failed to save. Please try again.")
        } finally {
            setLoading(false)
        }
    }

    // ── Step 3 — save products ───────────────────────────────────────────────
    const handleStep3Next = async () => {
        setLoading(true)
        setError("")
        try {
            if (csvMode && csvFile) {
                const form = new FormData()
                form.append("file", csvFile)
                await api.post(`/api/brands/${brandId}/products/csv`, form, {
                    headers: { "Content-Type": "multipart/form-data" }
                })
            } else {
                const valid = products.filter(p => p.name.trim() && p.selling_price)
                for (const p of valid) {
                    await api.post(`/api/brands/${brandId}/products`, {
                        name: p.name.trim(),
                        selling_price: parseFloat(p.selling_price),
                        cost_price: p.cost_price ? parseFloat(p.cost_price) : null,
                        current_stock: parseInt(p.current_stock) || 0,
                        sku_code: p.sku_code || null,
                    })
                }
            }
            setStep(4)
        } catch {
            setError("Failed to save products. Check your data and try again.")
        } finally {
            setLoading(false)
        }
    }

    // ── Final — complete onboarding ──────────────────────────────────────────
    const handleComplete = async () => {
        setLoading(true)
        try {
            await api.patch(`/api/brands/${brandId}`, { onboarding_completed: true })
            onComplete()
        } catch {
            onComplete() // proceed regardless
        } finally {
            setLoading(false)
        }
    }

    const togglePayment = (val: string) => {
        setPaymentMethods(prev =>
            prev.includes(val) ? prev.filter(m => m !== val) : [...prev, val]
        )
    }

    const updateProduct = (i: number, field: keyof ProductRow, val: string) => {
        setProducts(prev => prev.map((p, idx) => idx === i ? { ...p, [field]: val } : p))
    }

    // ── Layout shell ─────────────────────────────────────────────────────────
    return (
        <div className="min-h-screen bg-white flex flex-col items-center py-10 px-6">
            <div className="w-full max-w-xl">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="flex items-center justify-center gap-2 mb-6">
                        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        <span className="font-bold text-xl text-slate-900">ORYNT</span>
                    </div>
                    <h1 className="text-2xl font-bold text-slate-900">Set up {brandName}</h1>
                    <p className="text-slate-500 text-sm mt-1">Step {step} of {totalSteps}</p>
                    {/* Progress bar */}
                    <div className="w-full bg-slate-100 rounded-full h-1.5 mt-4">
                        <div
                            className="bg-primary h-1.5 rounded-full transition-all duration-500"
                            style={{ width: `${(step / totalSteps) * 100}%` }}
                        />
                    </div>
                </div>

                {error && (
                    <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-2xl">
                        {error}
                    </div>
                )}

                {/* ── STEP 1: Seller Type ─────────────────────────────── */}
                {step === 1 && (
                    <div className="space-y-4">
                        <div>
                            <h2 className="text-lg font-bold text-slate-900 mb-1">How do you sell?</h2>
                            <p className="text-slate-500 text-sm">Choose the option that best describes your business.</p>
                        </div>
                        <div className="space-y-3">
                            {SELLER_TYPES.map(opt => (
                                <button
                                    key={opt.value}
                                    onClick={() => setSellerType(opt.value)}
                                    className={cn(
                                        "w-full flex items-center gap-4 p-4 rounded-2xl border-2 text-left transition-all",
                                        sellerType === opt.value
                                            ? "border-primary bg-primary/5"
                                            : "border-slate-100 hover:border-slate-200"
                                    )}
                                >
                                    <div className={cn("p-2.5 rounded-xl", sellerType === opt.value ? "bg-primary text-white" : "bg-slate-100 text-slate-500")}>
                                        <opt.icon className="w-5 h-5" />
                                    </div>
                                    <div>
                                        <p className="font-bold text-slate-900 text-sm">{opt.label}</p>
                                        <p className="text-slate-400 text-xs mt-0.5">{opt.sub}</p>
                                    </div>
                                    {sellerType === opt.value && <CheckCircle2 className="w-5 h-5 text-primary ml-auto" />}
                                </button>
                            ))}
                        </div>
                        <button
                            onClick={handleStep1Next}
                            disabled={!sellerType || loading}
                            className="w-full h-12 bg-primary text-white font-bold rounded-2xl hover:opacity-90 disabled:opacity-40 transition-all flex items-center justify-center gap-2 mt-2"
                        >
                            {loading ? "Saving..." : "Continue"} <ArrowRight className="w-4 h-4" />
                        </button>
                    </div>
                )}

                {/* ── STEP 2: Payment Methods ─────────────────────────── */}
                {step === 2 && (
                    <div className="space-y-4">
                        <div>
                            <h2 className="text-lg font-bold text-slate-900 mb-1">How do you collect payment?</h2>
                            <p className="text-slate-500 text-sm">Select all that apply — you can add more later.</p>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            {PAYMENT_METHODS.map(opt => (
                                <button
                                    key={opt.value}
                                    onClick={() => togglePayment(opt.value)}
                                    className={cn(
                                        "flex items-center gap-3 p-4 rounded-2xl border-2 text-left transition-all",
                                        paymentMethods.includes(opt.value)
                                            ? "border-primary bg-primary/5"
                                            : "border-slate-100 hover:border-slate-200"
                                    )}
                                >
                                    {paymentMethods.includes(opt.value)
                                        ? <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0" />
                                        : <div className="w-5 h-5 rounded-full border-2 border-slate-200 flex-shrink-0" />
                                    }
                                    <span className="font-semibold text-slate-800 text-sm">{opt.label}</span>
                                </button>
                            ))}
                        </div>
                        <div className="flex gap-3 mt-2">
                            <button onClick={() => setStep(1)} className="flex items-center gap-2 px-5 h-12 rounded-2xl border-2 border-slate-100 text-slate-600 font-bold hover:border-slate-200 transition-all">
                                <ArrowLeft className="w-4 h-4" /> Back
                            </button>
                            <button
                                onClick={handleStep2Next}
                                disabled={paymentMethods.length === 0 || loading}
                                className="flex-1 h-12 bg-primary text-white font-bold rounded-2xl hover:opacity-90 disabled:opacity-40 transition-all flex items-center justify-center gap-2"
                            >
                                {loading ? "Saving..." : "Continue"} <ArrowRight className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                )}

                {/* ── STEP 3: Product Catalog (non-website sellers) ───── */}
                {step === 3 && needsProductCatalog && (
                    <div className="space-y-4">
                        <div>
                            <h2 className="text-lg font-bold text-slate-900 mb-1">Add your product catalog</h2>
                            <p className="text-slate-500 text-sm">
                                {isDigital ? "Add your digital products — they'll be marked as digital automatically." : "Add your products so ORYNT can score them for you."}
                            </p>
                        </div>

                        {/* Mode toggle */}
                        <div className="flex gap-2 bg-slate-50 p-1 rounded-2xl">
                            <button onClick={() => setCsvMode(false)} className={cn("flex-1 py-2 text-sm font-bold rounded-xl transition-all", !csvMode ? "bg-white shadow-sm text-slate-900" : "text-slate-400")}>
                                Manual Entry
                            </button>
                            <button onClick={() => setCsvMode(true)} className={cn("flex-1 py-2 text-sm font-bold rounded-xl transition-all", csvMode ? "bg-white shadow-sm text-slate-900" : "text-slate-400")}>
                                Upload CSV
                            </button>
                        </div>

                        {!csvMode ? (
                            <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                                {products.map((p, i) => (
                                    <div key={i} className="bg-slate-50 rounded-2xl p-4 space-y-3">
                                        <div className="flex gap-2">
                                            <input
                                                className="flex-1 h-10 px-3 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                                                style={{ backgroundColor: "#FFFFFF", color: "#1E293B", caretColor: "#00C9A7" }}
                                                placeholder="Product name *"
                                                value={p.name}
                                                onChange={e => updateProduct(i, "name", e.target.value)}
                                            />
                                            {products.length > 1 && (
                                                <button onClick={() => setProducts(prev => prev.filter((_, idx) => idx !== i))} className="text-slate-400 hover:text-red-500 p-2 rounded-xl transition-colors">
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            )}
                                        </div>
                                        <div className="grid grid-cols-3 gap-2">
                                            <input className="h-10 px-3 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" style={{ backgroundColor: "#FFFFFF", color: "#1E293B", caretColor: "#00C9A7" }} placeholder="Selling price *" value={p.selling_price} onChange={e => updateProduct(i, "selling_price", e.target.value)} />
                                            <input className="h-10 px-3 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" style={{ backgroundColor: "#FFFFFF", color: "#1E293B", caretColor: "#00C9A7" }} placeholder="Cost price" value={p.cost_price} onChange={e => updateProduct(i, "cost_price", e.target.value)} />
                                            {!isDigital && <input className="h-10 px-3 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" style={{ backgroundColor: "#FFFFFF", color: "#1E293B", caretColor: "#00C9A7" }} placeholder="Stock qty" value={p.current_stock} onChange={e => updateProduct(i, "current_stock", e.target.value)} />}
                                        </div>
                                    </div>
                                ))}
                                <button onClick={() => setProducts(prev => [...prev, emptyProduct()])} className="w-full h-10 border-2 border-dashed border-slate-200 rounded-2xl text-slate-400 hover:border-primary/30 hover:text-primary transition-all text-sm font-semibold flex items-center justify-center gap-2">
                                    <Plus className="w-4 h-4" /> Add another product
                                </button>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                <a
                                    href="/csv-template.csv"
                                    download
                                    className="text-primary text-sm font-semibold underline underline-offset-2"
                                >
                                    Download CSV template
                                </a>
                                <div
                                    onClick={() => fileRef.current?.click()}
                                    className={cn("border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-colors", csvFile ? "border-primary/40 bg-primary/5" : "border-slate-200 hover:border-primary/20")}
                                >
                                    <Upload className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                                    <p className="text-sm font-semibold text-slate-600">{csvFile ? csvFile.name : "Click to upload your CSV file"}</p>
                                    <p className="text-xs text-slate-400 mt-1">Columns: name, selling_price, cost_price, current_stock, sku_code</p>
                                </div>
                                <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={e => setCsvFile(e.target.files?.[0] ?? null)} />
                            </div>
                        )}

                        <div className="flex gap-3">
                            <button onClick={() => setStep(2)} className="flex items-center gap-2 px-5 h-12 rounded-2xl border-2 border-slate-100 text-slate-600 font-bold hover:border-slate-200 transition-all">
                                <ArrowLeft className="w-4 h-4" /> Back
                            </button>
                            <button onClick={handleStep3Next} disabled={loading} className="flex-1 h-12 bg-primary text-white font-bold rounded-2xl hover:opacity-90 disabled:opacity-40 transition-all flex items-center justify-center gap-2">
                                {loading ? "Saving..." : "Continue"} <ArrowRight className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                )}

                {/* ── STEP 4: Social & Ads (optional) ────────────────── */}
                {step === 4 && (
                    <div className="space-y-6">
                        <div>
                            <h2 className="text-lg font-bold text-slate-900 mb-1">Connect social & ads accounts</h2>
                            <p className="text-slate-500 text-sm">Optional — you can connect these later from the Integrations page.</p>
                        </div>

                        <div className="space-y-3">
                            {[
                                { name: "Instagram Business", desc: "Post & story performance data", available: false },
                                { name: "Facebook Page", desc: "Page insights & engagement", available: false },
                                { name: "Meta Ads Account", desc: "Ad spend, impressions & ROAS", available: false },
                            ].map(item => (
                                <div key={item.name} className="flex items-center justify-between p-4 rounded-2xl border border-slate-100 bg-slate-50">
                                    <div>
                                        <p className="font-bold text-slate-800 text-sm">{item.name}</p>
                                        <p className="text-slate-400 text-xs">{item.desc}</p>
                                    </div>
                                    <span className="text-[10px] font-bold bg-slate-200 text-slate-500 px-2.5 py-1 rounded-full">
                                        Coming in Sprint 1.11
                                    </span>
                                </div>
                            ))}
                        </div>

                        <div className="flex gap-3">
                            <button onClick={() => setStep(needsProductCatalog ? 3 : 2)} className="flex items-center gap-2 px-5 h-12 rounded-2xl border-2 border-slate-100 text-slate-600 font-bold hover:border-slate-200 transition-all">
                                <ArrowLeft className="w-4 h-4" /> Back
                            </button>
                            <button
                                onClick={handleComplete}
                                disabled={loading}
                                className="flex-1 h-12 bg-primary text-white font-bold rounded-2xl hover:opacity-90 disabled:opacity-40 transition-all flex items-center justify-center gap-2"
                            >
                                {loading ? "Finishing..." : "Go to Dashboard"} <ArrowRight className="w-4 h-4" />
                            </button>
                        </div>
                        <button onClick={handleComplete} className="w-full text-slate-400 text-sm font-semibold flex items-center justify-center gap-2 hover:text-slate-600 transition-colors">
                            <SkipForward className="w-4 h-4" /> Skip for now
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}
