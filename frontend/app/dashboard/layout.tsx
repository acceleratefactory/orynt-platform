"use client"

import { Sidebar } from "@/components/dashboard/sidebar"
import { Header } from "@/components/dashboard/header"

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <div className="min-h-screen" style={{ backgroundColor: "var(--color-bg)" }}>
            <Sidebar />
            {/* 240px left margin = sidebar width; 64px top = header height */}
            <div className="ml-60 flex flex-col min-h-screen">
                <Header />
                <main
                    className="flex-1 mt-16"
                    style={{ backgroundColor: "var(--color-bg)" }}
                >
                    {children}
                </main>
            </div>
        </div>
    )
}
