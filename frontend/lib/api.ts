import axios from "axios"
import { supabase } from "./supabase"

const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    headers: {
        "Content-Type": "application/json",
    },
    timeout: 30000,
})

// Attach Supabase JWT to every request
api.interceptors.request.use(async (config) => {
    const { data: { session } } = await supabase.auth.getSession()
    const token = session?.access_token

    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }

    return config
})

export default api
