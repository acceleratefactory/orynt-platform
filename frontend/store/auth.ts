import { create } from "zustand"
import { Session, User } from "@supabase/supabase-js"
import { supabase } from "@/lib/supabase"

interface AuthState {
    user: User | null
    session: Session | null
    isLoading: boolean
    isAuthenticated: boolean
    setSession: (session: Session | null) => void
    setLoading: (loading: boolean) => void
    clearSession: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
    user: null,
    session: null,
    isLoading: true,
    isAuthenticated: false,
    setSession: (session) =>
        set({
            session,
            user: session?.user ?? null,
            isAuthenticated: !!session,
            isLoading: false,
        }),
    setLoading: (isLoading) => set({ isLoading }),
    clearSession: async () => {
        await supabase.auth.signOut()
        set({ user: null, session: null, isAuthenticated: false, isLoading: false })
    },
}))

// Initialization logic to hydrate the store from Supabase
export const initAuth = async () => {
    const { setSession, setLoading } = useAuthStore.getState()

    try {
        const { data: { session } } = await supabase.auth.getSession()
        setSession(session)
    } catch (error) {
        console.error("Error hydrating auth session:", error)
        setSession(null)
    } finally {
        setLoading(false)
    }

    // Listen for auth state changes
    supabase.auth.onAuthStateChange((_event, session) => {
        setSession(session)
    })
}
