"use client"

import { useAuthStore } from "@/store/auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import api from "@/lib/api"

export default function DashboardPage() {
    const { user, clearSession } = useAuthStore()
    const router = useRouter()
    const [backendUser, setBackendUser] = useState<any>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        async function fetchMe() {
            try {
                const response = await api.get("/auth/me")
                setBackendUser(response.data)
            } catch (error) {
                console.error("Failed to fetch backend user:", error)
            } finally {
                setLoading(false)
            }
        }
        fetchMe()
    }, [])

    const handleLogout = async () => {
        await clearSession()
        router.push("/auth/login")
    }

    return (
        <div className="min-h-screen bg-slate-950 text-white p-8">
            <div className="max-w-4xl mx-auto space-y-8">
                <div className="flex justify-between items-center">
                    <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                    <Button
                        variant="outline"
                        onClick={handleLogout}
                        className="border-slate-800 text-slate-400 hover:text-white hover:bg-slate-900"
                    >
                        Log out
                    </Button>
                </div>

                <div className="grid gap-6 md:grid-cols-2">
                    {/* Frontend Session Info */}
                    <Card className="bg-slate-900 border-slate-800 text-white">
                        <CardHeader>
                            <CardTitle>Frontend Session</CardTitle>
                            <CardDescription className="text-slate-400">
                                Data from Zustand / Supabase Auth
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-slate-400">Email:</span>
                                <span className="font-mono">{user?.email}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-slate-400">User ID:</span>
                                <span className="font-mono text-[10px] sm:text-xs">{user?.id}</span>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Backend Verification Info */}
                    <Card className="bg-slate-900 border-slate-800 text-white">
                        <CardHeader>
                            <CardTitle>Backend Verification</CardTitle>
                            <CardDescription className="text-slate-400">
                                Verified via JWT on FastAPI /auth/me
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            {loading ? (
                                <div className="animate-pulse flex space-x-4">
                                    <div className="flex-1 space-y-4 py-1">
                                        <div className="h-4 bg-slate-800 rounded w-3/4"></div>
                                        <div className="h-4 bg-slate-800 rounded"></div>
                                    </div>
                                </div>
                            ) : backendUser ? (
                                <>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-slate-400">Authenticated:</span>
                                        <span className="text-emerald-500 font-semibold">Yes ✅</span>
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-slate-400">Backend Email:</span>
                                        <span className="font-mono">{backendUser.email}</span>
                                    </div>
                                </>
                            ) : (
                                <p className="text-red-400 text-sm">Failed to verify with backend.</p>
                            )}
                        </CardContent>
                    </Card>
                </div>

                <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-lg p-6">
                    <h3 className="text-emerald-500 font-semibold mb-2">Auth Flow Verified!</h3>
                    <p className="text-slate-400 text-sm leading-relaxed">
                        You are currently on a protected route. Refreshing this page will hydrate the session from local storage.
                        Logging out will clear the session and redirect you back to the login screen.
                    </p>
                </div>
            </div>
        </div>
    )
}
