import type { Metadata } from "next"
import "./globals.css"
import { AuthProvider } from "@/components/auth-provider"

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
    <html lang="en" suppressHydrationWarning style={{ backgroundColor: "#0A0A0F" }}>
      <body style={{ fontFamily: "'DM Sans', sans-serif", backgroundColor: "#0A0A0F" }}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
