"use client"

import { useEffect, useState } from "react"

interface HealthResponse {
  status: string
  service: string
  database: string
  cache: string
  environment: string
}

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [connected, setConnected] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

    fetch(`${apiUrl}/health`)
      .then((res) => {
        if (!res.ok) throw new Error("API responded with non-200 status")
        return res.json()
      })
      .then((data: HealthResponse) => {
        setHealth(data)
        setConnected(data.status === "ok")
        setLoading(false)
      })
      .catch(() => {
        setConnected(false)
        setLoading(false)
      })
  }, [])

  return (
    <main className="min-h-screen bg-slate-950 flex items-center justify-center p-8">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-10 max-w-md w-full shadow-2xl">
        {/* Logo / Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white tracking-tight">ORYNT</h1>
          <p className="text-slate-400 text-sm mt-1">Platform API Connection Test</p>
        </div>

        {/* Status Card */}
        <div className={`rounded-xl p-6 border text-center transition-all ${loading
            ? "bg-slate-800 border-slate-700"
            : connected
              ? "bg-emerald-950 border-emerald-800"
              : "bg-red-950 border-red-800"
          }`}>
          {loading ? (
            <p className="text-slate-300 text-lg animate-pulse">Connecting to API…</p>
          ) : connected ? (
            <p className="text-emerald-400 text-xl font-semibold">ORYNT API: Connected ✅</p>
          ) : (
            <p className="text-red-400 text-xl font-semibold">ORYNT API: Disconnected ❌</p>
          )}
        </div>

        {/* Details */}
        {health && (
          <div className="mt-6 space-y-2 text-sm">
            <div className="flex justify-between text-slate-400">
              <span>Environment</span>
              <span className="text-white font-mono">{health.environment}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Database</span>
              <span className={health.database === "connected" ? "text-emerald-400" : "text-red-400"}>
                {health.database}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Cache</span>
              <span className={health.cache === "connected" ? "text-emerald-400" : "text-red-400"}>
                {health.cache}
              </span>
            </div>
          </div>
        )}

        {/* Footer */}
        <p className="text-slate-600 text-xs text-center mt-8">
          Sprint 0.4 — Local verification page · Replace in Sprint 0.6
        </p>
      </div>
    </main>
  )
}
