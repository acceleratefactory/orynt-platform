"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { supabase } from "@/lib/supabase"
import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useToast } from "@/hooks/use-toast"
import { useAuthStore } from "@/store/auth"

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

        const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password,
        })

        if (error) {
            toast({
                variant: "destructive",
                title: "Login failed",
                description: "Invalid email or password.",
            })
            setLoading(false)
        } else {
            setSession(data.session)
            router.push("/dashboard")
        }
    }

    const handleMagicLink = async () => {
        if (!email) {
            toast({
                variant: "destructive",
                title: "Email required",
                description: "Please enter your email to receive a magic link.",
            })
            return
        }

        setMagicLinkLoading(true)
        const { error } = await supabase.auth.signInWithOtp({
            email,
            options: {
                emailRedirectTo: `${window.location.origin}/dashboard`,
            },
        })

        if (error) {
            toast({
                variant: "destructive",
                title: "Error",
                description: error.message,
            })
        } else {
            toast({
                title: "Check your email",
                description: "We've sent you a magic link to sign in.",
            })
        }
        setMagicLinkLoading(false)
    }

    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
            <Card className="w-full max-w-md bg-slate-900 border-slate-800 text-white">
                <CardHeader className="space-y-1">
                    <CardTitle className="text-2xl font-bold">Log in</CardTitle>
                    <CardDescription className="text-slate-400">
                        Enter your credentials to access your dashboard.
                    </CardDescription>
                </CardHeader>
                <form onSubmit={handleLogin}>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="name@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                className="bg-slate-950 border-slate-800"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="password">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                className="bg-slate-950 border-slate-800"
                            />
                        </div>
                    </CardContent>
                    <CardFooter className="flex flex-col space-y-4">
                        <Button
                            type="submit"
                            className="w-full bg-emerald-600 hover:bg-emerald-700"
                            disabled={loading || magicLinkLoading}
                        >
                            {loading ? "Logging in..." : "Log In"}
                        </Button>

                        <div className="relative w-full">
                            <div className="absolute inset-0 flex items-center">
                                <span className="w-full border-t border-slate-800" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-slate-900 px-2 text-slate-400">Or continue with</span>
                            </div>
                        </div>

                        <Button
                            type="button"
                            variant="outline"
                            className="w-full border-slate-800 text-slate-300 hover:bg-slate-800 hover:text-white"
                            onClick={handleMagicLink}
                            disabled={loading || magicLinkLoading}
                        >
                            {magicLinkLoading ? "Sending link..." : "Sign in with Magic Link"}
                        </Button>

                        <div className="text-sm text-center text-slate-400">
                            Don&apos;t have an account?{" "}
                            <Link href="/auth/signup" className="text-emerald-500 hover:underline">
                                Sign up
                            </Link>
                        </div>
                    </CardFooter>
                </form>
            </Card>
        </div>
    )
}
