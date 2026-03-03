"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { supabase } from "@/lib/supabase"
import { useToast } from "@/hooks/use-toast"
import { useAuthStore } from "@/store/auth"
import { Mail, Lock, Zap } from "lucide-react"

export default function LoginPage() {
    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [loading, setLoading] = useState(false)
    const [magicLinkLoading, setMagicLinkLoading] = useState(false)
    const router = useRouter()
    const { toast } = useToast()
    const { setSession } = useAuthStore()

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        const { data, error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) {
            toast({ variant: "destructive", title: "Login failed", description: "Invalid email or password." })
            setLoading(false)
        } else {
            setSession(data.session)
            router.push("/dashboard")
        }
    }

    const handleMagicLink = async () => {
        if (!email) {
            toast({ variant: "destructive", title: "Email required", description: "Enter your email first." })
            return
        }
        setMagicLinkLoading(true)
        const { error } = await supabase.auth.signInWithOtp({
            email,
            options: { emailRedirectTo: `${window.location.origin}/dashboard` },
        })
        if (error) {
            toast({ variant: "destructive", title: "Error", description: error.message })
        } else {
            toast({ title: "Check your email", description: "We've sent you a magic link to sign in." })
        }
        setMagicLinkLoading(false)
    }

    // Shared input style — always dark text regardless of theme
    const inputBase = {
        color: "#0A0A0F",
        backgroundColor: "#F8F9FA",
        caretColor: "#00C9A7",
    }

    return (
        <div className="min-h-screen bg-white flex" style={{ color: "#0A0A0F" }}>
            {/* Left decorative panel */}
            <div className="hidden lg:flex lg:w-1/2 bg-[#0F172A] flex-col items-center justify-center p-16 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-full">
                    <div className="absolute top-1/4 left-1/4 w-64 h-64 rounded-full blur-3xl" style={{ backgroundColor: "rgba(0,201,167,0.15)" }} />
                    <div className="absolute bottom-1/4 right-1/4 w-48 h-48 rounded-full blur-3xl" style={{ backgroundColor: "rgba(0,201,167,0.08)" }} />
                </div>
                <div className="relative z-10 text-center">
                    <div className="flex items-center justify-center gap-3 mb-12">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: "#00C9A7" }}>
                            <Zap className="w-6 h-6 text-white" />
                        </div>
                        <span className="text-white font-bold text-2xl tracking-widest" style={{ fontFamily: "var(--font-display, Syne, sans-serif)", letterSpacing: "0.12em" }}>ORYNT</span>
                    </div>
                    <h2 className="text-4xl font-bold text-white leading-tight mb-4">
                        Your AI-powered<br />brand intelligence
                    </h2>
                    <p className="text-slate-400 text-lg">
                        The unfair advantage for Nigerian SMEs.
                    </p>
                </div>
            </div>

            {/* Right form panel */}
            <div className="flex-1 flex items-center justify-center p-8 bg-white">
                <div className="w-full max-w-md space-y-8">
                    {/* Mobile logo */}
                    <div className="flex items-center gap-2 lg:hidden">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: "#00C9A7" }}>
                            <Zap className="w-5 h-5 text-white" />
                        </div>
                        <span className="font-bold text-xl" style={{ color: "#0A0A0F", fontFamily: "var(--font-display, Syne, sans-serif)" }}>ORYNT</span>
                    </div>

                    <div>
                        <h1 className="text-3xl font-bold" style={{ color: "#0A0A0F" }}>Welcome back</h1>
                        <p className="mt-2" style={{ color: "#6B7280" }}>Sign in to continue to your dashboard.</p>
                    </div>

                    <form onSubmit={handleLogin} className="space-y-5">
                        {/* Email */}
                        <div className="space-y-2">
                            <label htmlFor="email" className="block text-sm font-semibold" style={{ color: "#374151" }}>Email</label>
                            <div className="relative">
                                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: "#9CA3AF" }} />
                                <input
                                    id="email"
                                    type="email"
                                    placeholder="name@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    className="w-full pl-10 pr-4 h-12 rounded-2xl border-none outline-none text-sm font-medium transition-shadow"
                                    style={{
                                        ...inputBase,
                                        boxShadow: "0 0 0 2px transparent",
                                    }}
                                    onFocus={e => e.currentTarget.style.boxShadow = "0 0 0 2px rgba(0,201,167,0.4)"}
                                    onBlur={e => e.currentTarget.style.boxShadow = "0 0 0 2px transparent"}
                                />
                            </div>
                        </div>

                        {/* Password */}
                        <div className="space-y-2">
                            <label htmlFor="password" className="block text-sm font-semibold" style={{ color: "#374151" }}>Password</label>
                            <div className="relative">
                                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: "#9CA3AF" }} />
                                <input
                                    id="password"
                                    type="password"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    className="w-full pl-10 pr-4 h-12 rounded-2xl border-none outline-none text-sm font-medium transition-shadow"
                                    style={{
                                        ...inputBase,
                                        boxShadow: "0 0 0 2px transparent",
                                    }}
                                    onFocus={e => e.currentTarget.style.boxShadow = "0 0 0 2px rgba(0,201,167,0.4)"}
                                    onBlur={e => e.currentTarget.style.boxShadow = "0 0 0 2px transparent"}
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading || magicLinkLoading}
                            className="w-full h-12 font-bold rounded-2xl transition-opacity disabled:opacity-50"
                            style={{ backgroundColor: "#00C9A7", color: "#0A0A0F" }}
                            onMouseEnter={e => { if (!loading) e.currentTarget.style.backgroundColor = "#00B396" }}
                            onMouseLeave={e => e.currentTarget.style.backgroundColor = "#00C9A7"}
                        >
                            {loading ? "Signing in..." : "Sign In"}
                        </button>
                    </form>

                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-slate-100" />
                        </div>
                        <div className="relative flex justify-center text-xs">
                            <span className="bg-white px-3 font-semibold uppercase tracking-widest" style={{ color: "#9CA3AF" }}>
                                or continue with
                            </span>
                        </div>
                    </div>

                    <button
                        type="button"
                        onClick={handleMagicLink}
                        disabled={loading || magicLinkLoading}
                        className="w-full h-12 font-bold rounded-2xl border-2 border-slate-100 bg-white transition-all disabled:opacity-50"
                        style={{ color: "#374151" }}
                        onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(0,201,167,0.4)"; e.currentTarget.style.color = "#00C9A7" }}
                        onMouseLeave={e => { e.currentTarget.style.borderColor = "#F1F5F9"; e.currentTarget.style.color = "#374151" }}
                    >
                        {magicLinkLoading ? "Sending link..." : "✉️ Sign in with Magic Link"}
                    </button>

                    <p className="text-center text-sm" style={{ color: "#6B7280" }}>
                        Don&apos;t have an account?{" "}
                        <Link href="/auth/signup" className="font-bold hover:underline" style={{ color: "#00C9A7" }}>
                            Sign up
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
