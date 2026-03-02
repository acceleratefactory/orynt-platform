"use client"

import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useAuthStore } from "@/store/auth"

export function AuthGuard({ children }: { children: React.ReactNode }) {
    const { isAuthenticated, isLoading } = useAuthStore()
    const router = useRouter()
    const pathname = usePathname()

    useEffect(() => {
        if (!isLoading && !isAuthenticated && pathname.startsWith("/dashboard")) {
            router.push("/auth/login")
        }
    }, [isAuthenticated, isLoading, router, pathname])

    if (isLoading) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-emerald-500"></div>
            </div>
        )
    }

    if (!isAuthenticated && pathname.startsWith("/dashboard")) {
        return null // Prevents flicker while redirecting
    }

    return <>{children}</>
}
