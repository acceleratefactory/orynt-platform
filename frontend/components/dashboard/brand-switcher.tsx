"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { ChevronDown, CheckIcon, Plus, Tag } from "lucide-react"
import { cn } from "@/lib/utils"
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

    // Close dropdown if clicking outside
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) {
                setOpen(false)
            }
        }
        document.addEventListener("mousedown", handler)
        return () => document.removeEventListener("mousedown", handler)
    }, [])

    // Load brands and auto-set the first one if needed
    useEffect(() => {
        api.get("/api/brands").then((res) => {
            const list: Brand[] = res.data
            setBrands(list)
            if (list.length > 0 && !activeBrandId) {
                setActiveBrandId(list[0].id)
            }
        }).catch(() => {})
    }, [])

    const activeBrand = brands.find((b) => b.id === activeBrandId) ?? brands[0]
    const hasMultipleBrands = brands.length > 1

    const handleSelect = (brand: Brand) => {
        setActiveBrandId(brand.id)
        setOpen(false)
        // TanStack Query / components that depend on activeBrandId will re-fetch automatically
    }

    if (!activeBrand) {
        return (
            <div className="mx-4 h-12 rounded-2xl bg-slate-800/30 animate-pulse" />
        )
    }

    return (
        <div ref={ref} className="relative mx-4">
            <button
                onClick={() => hasMultipleBrands && setOpen((o) => !o)}
                className={cn(
                    "w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-200",
                    "bg-slate-800/40 border border-slate-700/40 text-left",
                    hasMultipleBrands
                        ? "hover:bg-slate-800/70 cursor-pointer"
                        : "cursor-default"
                )}
            >
                <div className="w-8 h-8 rounded-xl bg-primary/20 flex items-center justify-center flex-shrink-0">
                    <Tag className="w-4 h-4 text-primary" />
                </div>
                <div className="flex-1 overflow-hidden">
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest leading-none mb-0.5">
                        Active Brand
                    </p>
                    <p className="text-sm font-bold text-white truncate leading-tight">
                        {activeBrand.name}
                    </p>
                    <p className="text-[10px] text-slate-500 truncate leading-none mt-0.5">
                        {activeBrand.category}
                    </p>
                </div>
                {hasMultipleBrands && (
                    <ChevronDown
                        className={cn(
                            "w-4 h-4 text-slate-400 flex-shrink-0 transition-transform duration-200",
                            open && "rotate-180"
                        )}
                    />
                )}
            </button>

            {/* Dropdown */}
            {open && hasMultipleBrands && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-700/60 rounded-2xl shadow-2xl z-50 overflow-hidden">
                    <div className="p-2 space-y-0.5 max-h-64 overflow-y-auto">
                        {brands.map((brand) => (
                            <button
                                key={brand.id}
                                onClick={() => handleSelect(brand)}
                                className={cn(
                                    "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-colors",
                                    brand.id === activeBrandId
                                        ? "bg-primary/20 text-white"
                                        : "text-slate-300 hover:bg-slate-800"
                                )}
                            >
                                <div className="w-7 h-7 rounded-lg bg-slate-700 flex items-center justify-center flex-shrink-0">
                                    <Tag className="w-3.5 h-3.5 text-slate-400" />
                                </div>
                                <div className="flex-1 overflow-hidden">
                                    <p className="text-sm font-semibold truncate">{brand.name}</p>
                                    <p className="text-[10px] text-slate-500 truncate">{brand.category}</p>
                                </div>
                                {brand.id === activeBrandId && (
                                    <CheckIcon className="w-4 h-4 text-primary flex-shrink-0" />
                                )}
                            </button>
                        ))}
                    </div>

                    {/* Divider + Add New Brand */}
                    <div className="border-t border-slate-700/60 p-2">
                        <button
                            onClick={() => {
                                setOpen(false)
                                router.push("/dashboard/settings/brands/new")
                            }}
                            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl text-primary hover:bg-primary/10 transition-colors text-sm font-bold"
                        >
                            <Plus className="w-4 h-4" />
                            Add New Brand
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
