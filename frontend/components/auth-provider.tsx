"use client"

import { useEffect } from "react"
import { initAuth } from "@/store/auth"
import { AuthGuard } from "@/components/auth-guard"
import { Toaster } from "@/components/ui/toaster"

export function AuthProvider({ children }: { children: React.ReactNode }) {
    useEffect(() => {
        initAuth()
    }, [])

    return (
        <AuthGuard>
            {children}
            <Toaster />
        </AuthGuard>
    )
}
