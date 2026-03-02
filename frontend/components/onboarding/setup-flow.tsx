"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useToast } from "@/hooks/use-toast"
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
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
            <div className="w-full max-w-lg space-y-6">
                {/* Progress indicator */}
                <div className="flex items-center gap-3 justify-center">
                    <div className={`h-2 w-24 rounded-full ${step >= 1 ? "bg-emerald-500" : "bg-slate-700"}`} />
                    <div className={`h-2 w-24 rounded-full ${step === 2 ? "bg-emerald-500" : "bg-slate-700"}`} />
                </div>
                <p className="text-center text-slate-400 text-sm">Step {step} of 2</p>

                {step === 1 ? (
                    <Card className="bg-slate-900 border-slate-800 text-white">
                        <CardHeader>
                            <CardTitle className="text-2xl">Set up your organization</CardTitle>
                            <CardDescription className="text-slate-400">
                                This is your business account. You can have multiple brands under it.
                            </CardDescription>
                        </CardHeader>
                        <form onSubmit={handleOrgSubmit}>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="org-name">Business / Organization name</Label>
                                    <Input
                                        id="org-name"
                                        placeholder="e.g. Kemi's Fashion House"
                                        value={orgName}
                                        onChange={(e) => setOrgName(e.target.value)}
                                        required
                                        className="bg-slate-950 border-slate-800"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="phone">Phone number <span className="text-slate-500 text-xs">(optional)</span></Label>
                                    <Input
                                        id="phone"
                                        placeholder="+234 800 000 0000"
                                        value={phone}
                                        onChange={(e) => setPhone(e.target.value)}
                                        className="bg-slate-950 border-slate-800"
                                    />
                                </div>
                            </CardContent>
                            <CardFooter>
                                <Button
                                    type="submit"
                                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                                    disabled={loading}
                                >
                                    {loading ? "Saving..." : "Continue →"}
                                </Button>
                            </CardFooter>
                        </form>
                    </Card>
                ) : (
                    <Card className="bg-slate-900 border-slate-800 text-white">
                        <CardHeader>
                            <CardTitle className="text-2xl">Create your first brand</CardTitle>
                            <CardDescription className="text-slate-400">
                                A brand is the product line or store you want ORYNT to analyse.
                            </CardDescription>
                        </CardHeader>
                        <form onSubmit={handleBrandSubmit}>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="brand-name">Brand name</Label>
                                    <Input
                                        id="brand-name"
                                        placeholder="e.g. KemiFashion"
                                        value={brandName}
                                        onChange={(e) => setBrandName(e.target.value)}
                                        required
                                        className="bg-slate-950 border-slate-800"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="category">Category</Label>
                                    <select
                                        id="category"
                                        value={category}
                                        onChange={(e) => setCategory(e.target.value)}
                                        className="w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                                        required
                                    >
                                        <option value="" disabled>Select a category…</option>
                                        {CATEGORIES.map((c) => (
                                            <option key={c} value={c}>{c}</option>
                                        ))}
                                    </select>
                                </div>
                            </CardContent>
                            <CardFooter className="flex gap-3">
                                {skipToStep !== 2 && (
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="border-slate-800 text-slate-400"
                                        onClick={() => setStep(1)}
                                    >
                                        Back
                                    </Button>
                                )}
                                <Button
                                    type="submit"
                                    className="flex-1 bg-emerald-600 hover:bg-emerald-700"
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
