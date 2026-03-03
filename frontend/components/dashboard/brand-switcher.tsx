"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { ChevronDown, CheckIcon, Plus, Tag } from "lucide-react"
import { useAuthStore } from "@/store/auth"
import api from "@/lib/api"

interface Brand {
    id: string
    name: string
    category: string
}

export function BrandSwitcher() {
    const router = useRouter()
    const { activeBrandId, setActiveBrandId } = useAuthStore()
    const [brands, setBrands] = useState<Brand[]>([])
    const [open, setOpen] = useState(false)
    const ref = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
        }
        document.addEventListener("mousedown", handler)
        return () => document.removeEventListener("mousedown", handler)
    }, [])

    useEffect(() => {
        api.get("/api/brands").then((res) => {
            const list: Brand[] = res.data
            setBrands(list)
            if (list.length > 0 && !activeBrandId) setActiveBrandId(list[0].id)
        }).catch(() => {})
    }, [])

    const activeBrand = brands.find((b) => b.id === activeBrandId) ?? brands[0]
    const hasMultipleBrands = brands.length > 1

    const handleSelect = (brand: Brand) => {
        setActiveBrandId(brand.id)
        setOpen(false)
    }

    if (!activeBrand) {
        return (
            <div className="space-y-1">
                <div className="h-14 rounded-md animate-pulse" style={{ backgroundColor: "var(--color-surface-raised)" }} />
                <div className="h-7 rounded-md animate-pulse" style={{ backgroundColor: "var(--color-surface-raised)", opacity: 0.5 }} />
            </div>
        )
    }

    return (
        <div ref={ref} className="relative">
            {/* Active brand card */}
            <button
                onClick={() => hasMultipleBrands && setOpen((o) => !o)}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-md transition-all duration-150"
                style={{
                    backgroundColor: "var(--color-surface-raised)",
                    border: "1px solid var(--color-border)",
                    cursor: hasMultipleBrands ? "pointer" : "default",
                }}
                onMouseEnter={e => { if (hasMultipleBrands) e.currentTarget.style.borderColor = "var(--color-accent-border)" }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--color-border)" }}
            >
                {/* Brand icon */}
                <div
                    className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: "var(--color-accent-dim)" }}
                >
                    <Tag className="w-3 h-3" style={{ color: "var(--color-accent)" }} strokeWidth={1.5} />
                </div>
                <div className="flex-1 overflow-hidden text-left">
                    <p
                        className="text-[13px] font-semibold truncate font-body"
                        style={{ color: "var(--color-text-primary)" }}
                    >
                        {activeBrand.name}
                    </p>
                    <p
                        className="text-[11px] truncate font-body"
                        style={{ color: "var(--color-text-muted)" }}
                    >
                        {activeBrand.category}
                    </p>
                </div>
                {hasMultipleBrands && (
                    <ChevronDown
                        className="w-4 h-4 flex-shrink-0 transition-transform duration-150"
                        style={{ color: "var(--color-text-muted)", transform: open ? "rotate(180deg)" : "none" }}
                        strokeWidth={1.5}
                    />
                )}
            </button>

            {/* Dropdown — multi-brand only */}
            {open && hasMultipleBrands && (
                <div
                    className="absolute top-full left-0 right-0 mt-1 z-50 overflow-hidden rounded-lg"
                    style={{
                        backgroundColor: "var(--color-surface-raised)",
                        border: "1px solid var(--color-border)",
                        boxShadow: "var(--shadow-lg)",
                        minWidth: "220px",
                    }}
                >
                    <div className="p-2 space-y-0.5 max-h-80 overflow-y-auto">
                        {brands.map((brand) => (
                            <button
                                key={brand.id}
                                onClick={() => handleSelect(brand)}
                                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-left transition-colors duration-100 font-body"
                                style={brand.id === activeBrandId
                                    ? { backgroundColor: "var(--color-accent-dim)", color: "var(--color-text-primary)" }
                                    : { color: "var(--color-text-secondary)" }
                                }
                                onMouseEnter={e => { if (brand.id !== activeBrandId) e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.04)" }}
                                onMouseLeave={e => { if (brand.id !== activeBrandId) e.currentTarget.style.backgroundColor = "transparent" }}
                            >
                                <div>
                                    <p className="text-sm font-medium truncate">{brand.name}</p>
                                    <p className="text-[10px] truncate" style={{ color: "var(--color-text-muted)" }}>{brand.category}</p>
                                </div>
                                {brand.id === activeBrandId && (
                                    <CheckIcon className="w-4 h-4 ml-auto flex-shrink-0" style={{ color: "var(--color-accent)" }} strokeWidth={1.5} />
                                )}
                            </button>
                        ))}
                    </div>
                    {/* Divider */}
                    <div style={{ height: "1px", backgroundColor: "var(--color-border)", margin: "0 8px" }} />
                    {/* Add New Brand inside dropdown too */}
                    <div className="p-2">
                        <button
                            onClick={() => { setOpen(false); router.push("/dashboard/settings/brands/new") }}
                            className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-md text-sm font-medium font-body transition-colors duration-100"
                            style={{ color: "var(--color-accent)" }}
                            onMouseEnter={e => e.currentTarget.style.backgroundColor = "var(--color-accent-dim)"}
                            onMouseLeave={e => e.currentTarget.style.backgroundColor = "transparent"}
                        >
                            <Plus className="w-4 h-4" strokeWidth={1.5} />
                            Add New Brand
                        </button>
                    </div>
                </div>
            )}

            {/* Add New Brand — ALWAYS visible below the card */}
            <button
                onClick={() => { setOpen(false); router.push("/dashboard/settings/brands/new") }}
                className="w-full flex items-center gap-2 px-3 py-2 mt-1 rounded-md text-xs font-medium font-body transition-all duration-150"
                style={{ color: "var(--color-text-muted)" }}
                onMouseEnter={e => {
                    e.currentTarget.style.backgroundColor = "var(--color-accent-dim)"
                    e.currentTarget.style.color = "var(--color-accent)"
                }}
                onMouseLeave={e => {
                    e.currentTarget.style.backgroundColor = "transparent"
                    e.currentTarget.style.color = "var(--color-text-muted)"
                }}
            >
                <Plus className="w-3.5 h-3.5" strokeWidth={1.5} />
                Add New Brand
            </button>
        </div>
    )
}
