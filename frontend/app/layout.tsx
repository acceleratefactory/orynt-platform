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
            {/*
              Anti-flash script: runs synchronously before React hydrates.
              Reads orynt-theme from localStorage and sets data-theme on <html>
              so the correct CSS variables are active before first paint.
            */}
            <head>
                <script
                    dangerouslySetInnerHTML={{
                        __html: `
(function() {
  try {
    var saved = localStorage.getItem('orynt-theme');
    var theme = saved === 'light' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    if (theme === 'light') {
      document.documentElement.style.backgroundColor = '#F8F8FA';
    }
  } catch(e) {}
})();
                        `.trim()
                    }}
                />
            </head>
            <body className={dmSans.className} style={{ backgroundColor: "transparent" }}>
                <AuthProvider>
                    {children}
                </AuthProvider>
            </body>
        </html>
    )
}
