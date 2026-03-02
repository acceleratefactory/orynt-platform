"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { supabase } from "@/lib/supabase"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
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

    return (
        <div className="min-h-screen bg-white flex">
            {/* Left decorative panel */}
            <div className="hidden lg:flex lg:w-1/2 bg-[#0F172A] flex-col items-center justify-center p-16 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-full">
                    <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-primary/20 rounded-full blur-3xl" />
                    <div className="absolute bottom-1/4 right-1/4 w-48 h-48 bg-violet-500/10 rounded-full blur-3xl" />
                </div>
                <div className="relative z-10 text-center">
                    <div className="flex items-center justify-center gap-3 mb-12">
                        <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
                            <Zap className="w-6 h-6 text-white" />
                        </div>
                        <span className="text-white font-bold text-2xl tracking-tight">ORYNT</span>
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
            <div className="flex-1 flex items-center justify-center p-8">
                <div className="w-full max-w-md space-y-8">
                    {/* Mobile logo */}
                    <div className="flex items-center gap-2 lg:hidden">
                        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                            <Zap className="w-5 h-5 text-white" />
                        </div>
                        <span className="font-bold text-xl text-slate-900">ORYNT</span>
                    </div>

                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Welcome back</h1>
                        <p className="text-slate-500 mt-2">Sign in to continue to your dashboard.</p>
                    </div>

                    <form onSubmit={handleLogin} className="space-y-5">
                        <div className="space-y-2">
                            <Label htmlFor="email" className="text-slate-700 font-semibold">Email</Label>
                            <div className="relative">
                                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="name@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    className="pl-10 h-12 bg-slate-50 border-none rounded-2xl focus-visible:ring-primary/30"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="password" className="text-slate-700 font-semibold">Password</Label>
                            <div className="relative">
                                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                                <Input
                                    id="password"
                                    type="password"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    className="pl-10 h-12 bg-slate-50 border-none rounded-2xl focus-visible:ring-primary/30"
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading || magicLinkLoading}
                            className="w-full h-12 bg-primary hover:opacity-90 active:scale-[0.98] transition-all text-white font-bold rounded-2xl premium-shadow"
                        >
                            {loading ? "Signing in..." : "Sign In"}
                        </button>
                    </form>

                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-slate-100" />
                        </div>
                        <div className="relative flex justify-center text-xs">
                            <span className="bg-white px-3 text-slate-400 font-semibold uppercase tracking-widest">
                                or continue with
                            </span>
                        </div>
                    </div>

                    <button
                        type="button"
                        onClick={handleMagicLink}
                        disabled={loading || magicLinkLoading}
                        className="w-full h-12 border-2 border-slate-100 bg-white text-slate-700 font-bold rounded-2xl hover:border-primary/30 hover:text-primary transition-all"
                    >
                        {magicLinkLoading ? "Sending link..." : "✉️ Sign in with Magic Link"}
                    </button>

                    <p className="text-center text-sm text-slate-500">
                        Don&apos;t have an account?{" "}
                        <Link href="/auth/signup" className="text-primary font-bold hover:underline">
                            Sign up
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
