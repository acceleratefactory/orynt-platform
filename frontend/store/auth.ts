import { create } from "zustand"

interface User {
    id: string
    email: string
}

interface AuthState {
    user: User | null
    token: string | null
    isLoading: boolean
    setUser: (user: User | null) => void
    setToken: (token: string | null) => void
    setLoading: (loading: boolean) => void
    logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
    user: null,
    token: null,
    isLoading: true,
    setUser: (user) => set({ user }),
    setToken: (token) => set({ token }),
    setLoading: (isLoading) => set({ isLoading }),
    logout: () => set({ user: null, token: null }),
}))
