"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useToast } from "@/hooks/use-toast"
import { cn } from "@/lib/utils"
import api from "@/lib/api"

const CATEGORIES = [
    "Fashion",
    "Food & Beverage",
    "Beauty & Skincare",
    "Electronics",
    "Home & Living",
    "Health & Wellness",
    "Digital Products",
    "Other",
]

interface SetupFlowProps {
    onComplete: () => void
    skipToStep?: 2
}

export function SetupFlow({ onComplete, skipToStep }: SetupFlowProps) {
    const [step, setStep] = useState<1 | 2>(skipToStep === 2 ? 2 : 1)
    const [orgName, setOrgName] = useState("")
    const [phone, setPhone] = useState("")
    const [brandName, setBrandName] = useState("")
    const [category, setCategory] = useState("")
    const [loading, setLoading] = useState(false)
    const { toast } = useToast()
    const router = useRouter()

    const handleOrgSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        try {
            await api.post("/api/organizations", { name: orgName, owner_phone: phone })
            setStep(2)
        } catch (err: any) {
            toast({
                variant: "destructive",
                title: "Error",
                description: err?.response?.data?.detail || "Failed to create organization.",
            })
        } finally {
            setLoading(false)
        }
    }

    const handleBrandSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!category) {
            toast({ variant: "destructive", title: "Please select a category." })
            return
        }
        setLoading(true)
        try {
            await api.post("/api/brands", { name: brandName, category })
            toast({ title: "Brand created!", description: `${brandName} is ready.` })
            onComplete()
        } catch (err: any) {
            toast({
                variant: "destructive",
                title: "Error",
                description: err?.response?.data?.detail || "Failed to create brand.",
            })
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-white flex items-center justify-center p-4">
            <div className="w-full max-w-lg space-y-6">
                {/* Progress indicator */}
                <div className="flex items-center gap-3 justify-center">
                    <div className={cn("h-2 w-24 rounded-full transition-colors", step >= 1 ? "bg-primary" : "bg-slate-100")} />
                    <div className={cn("h-2 w-24 rounded-full transition-colors", step === 2 ? "bg-primary" : "bg-slate-100")} />
                </div>
                <p className="text-center text-slate-400 text-xs font-bold uppercase tracking-widest">Step {step} of 2</p>

                {step === 1 ? (
                    <Card className="premium-shadow border-none rounded-[32px] overflow-hidden bg-white">
                        <CardHeader className="pt-10 px-10 text-center">
                            <CardTitle className="text-3xl font-bold text-slate-900">Set up your organization</CardTitle>
                            <CardDescription className="text-slate-500 mt-2">
                                This is your business account. You can have multiple brands under it.
                            </CardDescription>
                        </CardHeader>
                        <form onSubmit={handleOrgSubmit}>
                            <CardContent className="space-y-6 px-10 pb-8">
                                <div className="space-y-2">
                                    <Label htmlFor="org-name" className="text-slate-700 font-bold">Business / Organization name</Label>
                                    <Input
                                        id="org-name"
                                        placeholder="e.g. Kemi's Fashion House"
                                        value={orgName}
                                        onChange={(e) => setOrgName(e.target.value)}
                                        required
                                        className="h-12 bg-slate-50 border-none rounded-2xl focus-visible:ring-primary/20"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="phone" className="text-slate-700 font-bold">Phone number <span className="text-slate-400 font-normal text-xs ml-1">(Optional)</span></Label>
                                    <Input
                                        id="phone"
                                        placeholder="+234 800 000 0000"
                                        value={phone}
                                        onChange={(e) => setPhone(e.target.value)}
                                        className="h-12 bg-slate-50 border-none rounded-2xl focus-visible:ring-primary/20"
                                    />
                                </div>
                            </CardContent>
                            <CardFooter className="px-10 pb-10">
                                <Button
                                    type="submit"
                                    className="w-full h-12 bg-primary hover:opacity-90 transition-opacity text-white font-bold rounded-2xl premium-shadow"
                                    disabled={loading}
                                >
                                    {loading ? "Saving..." : "Continue →"}
                                </Button>
                            </CardFooter>
                        </form>
                    </Card>
                ) : (
                    <Card className="premium-shadow border-none rounded-[32px] overflow-hidden bg-white">
                        <CardHeader className="pt-10 px-10 text-center">
                            <CardTitle className="text-3xl font-bold text-slate-900">Create your first brand</CardTitle>
                            <CardDescription className="text-slate-500 mt-2">
                                A brand is the product line or store you want ORYNT to analyse.
                            </CardDescription>
                        </CardHeader>
                        <form onSubmit={handleBrandSubmit}>
                            <CardContent className="space-y-6 px-10 pb-8">
                                <div className="space-y-2">
                                    <Label htmlFor="brand-name" className="text-slate-700 font-bold">Brand name</Label>
                                    <Input
                                        id="brand-name"
                                        placeholder="e.g. KemiFashion"
                                        value={brandName}
                                        onChange={(e) => setBrandName(e.target.value)}
                                        required
                                        className="h-12 bg-slate-50 border-none rounded-2xl focus-visible:ring-primary/20"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="category" className="text-slate-700 font-bold">Category</Label>
                                    <select
                                        id="category"
                                        value={category}
                                        onChange={(e) => setCategory(e.target.value)}
                                        className="w-full h-12 rounded-2xl border-none bg-slate-50 px-4 text-slate-900 font-medium text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 appearance-none"
                                        required
                                    >
                                        <option value="" disabled>Select a category…</option>
                                        {CATEGORIES.map((c) => (
                                            <option key={c} value={c}>{c}</option>
                                        ))}
                                    </select>
                                </div>
                            </CardContent>
                            <CardFooter className="px-10 pb-10 flex gap-3">
                                {skipToStep !== 2 && (
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        className="h-12 border-none text-slate-500 font-bold rounded-2xl"
                                        onClick={() => setStep(1)}
                                    >
                                        Back
                                    </Button>
                                )}
                                <Button
                                    type="submit"
                                    className="flex-1 h-12 bg-primary hover:opacity-90 transition-opacity text-white font-bold rounded-2xl premium-shadow"
                                    disabled={loading}
                                >
                                    {loading ? "Creating..." : "Create My Brand"}
                                </Button>
                            </CardFooter>
                        </form>
                    </Card>
                )}
            </div>
        </div>
    )
}
