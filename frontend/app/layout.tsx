import type { Metadata } from "next"
import { Syne, DM_Sans, JetBrains_Mono } from "next/font/google"
import "./globals.css"
import { AuthProvider } from "@/components/auth-provider"

const syne = Syne({
    subsets: ["latin"],
    weight: ["600", "700", "800"],
    variable: "--font-display",
    display: "swap",
})

const dmSans = DM_Sans({
    subsets: ["latin"],
    weight: ["400", "500", "600"],
    variable: "--font-body",
    display: "swap",
})

const jetbrainsMono = JetBrains_Mono({
    subsets: ["latin"],
    weight: ["400", "500"],
    variable: "--font-mono",
    display: "swap",
})

export const metadata: Metadata = {
    title: "ORYNT — AI-Powered Brand Intelligence",
    description: "Your unfair advantage in e-commerce.",
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html
            lang="en"
            suppressHydrationWarning
            className={`${syne.variable} ${dmSans.variable} ${jetbrainsMono.variable}`}
            style={{ backgroundColor: "#0A0A0F" }}
        >
            <body className={dmSans.className} style={{ backgroundColor: "#0A0A0F" }}>
                <AuthProvider>
                    {children}
                </AuthProvider>
            </body>
        </html>
    )
}
