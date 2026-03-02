"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { supabase } from "@/lib/supabase"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useToast } from "@/hooks/use-toast"
import { Mail, Lock, Zap } from "lucide-react"

export default function SignupPage() {
    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [confirmPassword, setConfirmPassword] = useState("")
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

    return (
        <div className="min-h-screen bg-white flex">
            {/* Left decorative panel */}
            <div className="hidden lg:flex lg:w-1/2 bg-[#0F172A] flex-col items-center justify-center p-16 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-full">
                    <div className="absolute top-1/3 left-1/3 w-56 h-56 bg-primary/20 rounded-full blur-3xl" />
                    <div className="absolute bottom-1/3 right-1/3 w-40 h-40 bg-violet-500/10 rounded-full blur-3xl" />
                </div>
                <div className="relative z-10 text-center">
                    <div className="flex items-center justify-center gap-3 mb-12">
                        <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
                            <Zap className="w-6 h-6 text-white" />
                        </div>
                        <span className="text-white font-bold text-2xl tracking-tight">ORYNT</span>
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
                        <h1 className="text-3xl font-bold text-slate-900">Create your account</h1>
                        <p className="text-slate-500 mt-2">Get started with ORYNT for free.</p>
                    </div>

                    <form onSubmit={handleSignup} className="space-y-5">
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
                                    placeholder="Min 8 characters"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    className="pl-10 h-12 bg-slate-50 border-none rounded-2xl focus-visible:ring-primary/30"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="confirm-password" className="text-slate-700 font-semibold">Confirm Password</Label>
                            <div className="relative">
                                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                                <Input
                                    id="confirm-password"
                                    type="password"
                                    placeholder="Repeat your password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    required
                                    className="pl-10 h-12 bg-slate-50 border-none rounded-2xl focus-visible:ring-primary/30"
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full h-12 bg-primary hover:opacity-90 active:scale-[0.98] transition-all text-white font-bold rounded-2xl premium-shadow"
                        >
                            {loading ? "Creating account..." : "Create Account"}
                        </button>
                    </form>

                    <p className="text-center text-sm text-slate-500">
                        Already have an account?{" "}
                        <Link href="/auth/login" className="text-primary font-bold hover:underline">
                            Log in
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
