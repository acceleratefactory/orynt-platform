"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { supabase } from "@/lib/supabase"
import { useToast } from "@/hooks/use-toast"
import { Mail, Lock, Eye, EyeOff, Zap } from "lucide-react"

export default function SignupPage() {
    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [confirmPassword, setConfirmPassword] = useState("")
    const [showPassword, setShowPassword] = useState(false)
    const [showConfirmPassword, setShowConfirmPassword] = useState(false)
    const [loading, setLoading] = useState(false)
    const router = useRouter()
    const { toast } = useToast()

    const handleSignup = async (e: React.FormEvent) => {
        e.preventDefault()
        if (password !== confirmPassword) {
            toast({ variant: "destructive", title: "Passwords don't match", description: "Please make sure your passwords match." })
            return
        }
        setLoading(true)
        const { error } = await supabase.auth.signUp({
            email,
            password,
            options: { emailRedirectTo: `${window.location.origin}/auth/login` },
        })
        if (error) {
            toast({ variant: "destructive", title: "Signup failed", description: error.message })
            setLoading(false)
        } else {
            toast({ title: "Check your email", description: "We've sent you a confirmation link to complete your signup." })
            router.push("/auth/login")
        }
    }

    // Always dark text — immune to theme variables
    const inputBase: React.CSSProperties = {
        color: "#0A0A0F",
        backgroundColor: "#F8F9FA",
        caretColor: "#00C9A7",
    }

    const focusRing = (e: React.FocusEvent<HTMLInputElement>) => {
        e.currentTarget.style.boxShadow = "0 0 0 2px rgba(0,201,167,0.4)"
    }
    const blurRing = (e: React.FocusEvent<HTMLInputElement>) => {
        e.currentTarget.style.boxShadow = "0 0 0 2px transparent"
    }

    return (
        <div className="min-h-screen bg-white flex" style={{ color: "#0A0A0F" }}>
            {/* Left decorative panel */}
            <div className="hidden lg:flex lg:w-1/2 bg-[#0F172A] flex-col items-center justify-center p-16 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-full">
                    <div className="absolute top-1/3 left-1/3 w-56 h-56 rounded-full blur-3xl" style={{ backgroundColor: "rgba(0,201,167,0.15)" }} />
                    <div className="absolute bottom-1/3 right-1/3 w-40 h-40 rounded-full blur-3xl" style={{ backgroundColor: "rgba(0,201,167,0.08)" }} />
                </div>
                <div className="relative z-10 text-center">
                    <div className="flex items-center justify-center gap-3 mb-12">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: "#00C9A7" }}>
                            <Zap className="w-6 h-6 text-white" />
                        </div>
                        <span className="text-white font-bold text-2xl tracking-widest" style={{ fontFamily: "var(--font-display, Syne, sans-serif)", letterSpacing: "0.12em" }}>ORYNT</span>
                    </div>
                    <h2 className="text-4xl font-bold text-white leading-tight mb-4">
                        Start your brand<br />intelligence journey
                    </h2>
                    <p className="text-slate-400 text-lg">
                        Join ORYNT. Understand your market<br />like never before.
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
                        <h1 className="text-3xl font-bold" style={{ color: "#0A0A0F" }}>Create your account</h1>
                        <p className="mt-2" style={{ color: "#6B7280" }}>Get started with ORYNT for free.</p>
                    </div>

                    <form onSubmit={handleSignup} className="space-y-5">
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
                                    style={{ ...inputBase, boxShadow: "0 0 0 2px transparent" }}
                                    onFocus={focusRing}
                                    onBlur={blurRing}
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
                                    type={showPassword ? "text" : "password"}
                                    placeholder="Min 8 characters"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    className="w-full pl-10 pr-12 h-12 rounded-2xl border-none outline-none text-sm font-medium transition-shadow"
                                    style={{ ...inputBase, boxShadow: "0 0 0 2px transparent" }}
                                    onFocus={focusRing}
                                    onBlur={blurRing}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(v => !v)}
                                    className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 rounded-md transition-colors"
                                    style={{ color: "#9CA3AF" }}
                                    onMouseEnter={e => e.currentTarget.style.color = "#00C9A7"}
                                    onMouseLeave={e => e.currentTarget.style.color = "#9CA3AF"}
                                    tabIndex={-1}
                                    aria-label={showPassword ? "Hide password" : "Show password"}
                                >
                                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            </div>
                        </div>

                        {/* Confirm Password */}
                        <div className="space-y-2">
                            <label htmlFor="confirm-password" className="block text-sm font-semibold" style={{ color: "#374151" }}>Confirm Password</label>
                            <div className="relative">
                                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: "#9CA3AF" }} />
                                <input
                                    id="confirm-password"
                                    type={showConfirmPassword ? "text" : "password"}
                                    placeholder="Repeat your password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    required
                                    className="w-full pl-10 pr-12 h-12 rounded-2xl border-none outline-none text-sm font-medium transition-shadow"
                                    style={{ ...inputBase, boxShadow: "0 0 0 2px transparent" }}
                                    onFocus={focusRing}
                                    onBlur={blurRing}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmPassword(v => !v)}
                                    className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 rounded-md transition-colors"
                                    style={{ color: "#9CA3AF" }}
                                    onMouseEnter={e => e.currentTarget.style.color = "#00C9A7"}
                                    onMouseLeave={e => e.currentTarget.style.color = "#9CA3AF"}
                                    tabIndex={-1}
                                    aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                                >
                                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full h-12 font-bold rounded-2xl transition-opacity disabled:opacity-50"
                            style={{ backgroundColor: "#00C9A7", color: "#0A0A0F" }}
                            onMouseEnter={e => { if (!loading) e.currentTarget.style.backgroundColor = "#00B396" }}
                            onMouseLeave={e => e.currentTarget.style.backgroundColor = "#00C9A7"}
                        >
                            {loading ? "Creating account..." : "Create Account"}
                        </button>
                    </form>

                    <p className="text-center text-sm" style={{ color: "#6B7280" }}>
                        Already have an account?{" "}
                        <Link href="/auth/login" className="font-bold hover:underline" style={{ color: "#00C9A7" }}>
                            Log in
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
