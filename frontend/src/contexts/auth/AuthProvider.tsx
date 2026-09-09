import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { useQueryClient } from '@tanstack/react-query'

import { AuthContext, type AuthContextValue, type SignOutResult, type SignUpResult } from '@/contexts/auth/AuthContext'
import { supabase } from '@/lib/supabase'
import { apiService } from '@/services/api/apiService'

export function AuthProvider({ children }: { children: ReactNode }) {
    const [session, setSession] = useState<Session | null>(null)
    const [loading, setLoading] = useState(true)
    const queryClient = useQueryClient()
    const previousUserIdRef = useRef<string | null>(null)

    useEffect(() => {
        apiService.setAuthHandlers({
            refreshToken: async () => {
                const { data, error } = await supabase.auth.refreshSession()
                return error ? null : (data.session?.access_token ?? null)
            },
            // Dropping the session is enough: ProtectedRoute takes it from here.
            onUnauthorized: async () => {
                await supabase.auth.signOut()
            },
        })

        return () => {
            apiService.setAuthHandlers(null)
        }
    }, [])

    useEffect(() => {
        let mounted = true

        const loadSession = async () => {
            const { data } = await supabase.auth.getSession()
            if (!mounted) {
                return
            }
            setSession(data.session)
            previousUserIdRef.current = data.session?.user?.id ?? null
            apiService.setToken(data.session?.access_token ?? null)
            setLoading(false)
        }

        void loadSession()

        const {
            data: { subscription },
        } = supabase.auth.onAuthStateChange((event, nextSession) => {
            const nextUserId = nextSession?.user?.id ?? null
            const previousUserId = previousUserIdRef.current

            if (
                event === 'SIGNED_OUT'
                || (previousUserId != null && nextUserId != null && previousUserId !== nextUserId)
            ) {
                queryClient.clear()
            }

            previousUserIdRef.current = nextUserId
            setSession(nextSession)
            apiService.setToken(nextSession?.access_token ?? null)
            setLoading(false)
        })

        return () => {
            mounted = false
            subscription.unsubscribe()
        }
    }, [queryClient])

    const signIn = useCallback(async (email: string, password: string) => {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        return { error: error?.message ?? null }
    }, [])

    const signUp = useCallback(async (email: string, password: string): Promise<SignUpResult> => {
        const { data, error } = await supabase.auth.signUp({ email, password })
        return {
            error: error?.message ?? null,
            needsEmailConfirmation: !error && data.session === null,
        }
    }, [])

    const signOut = useCallback(async (): Promise<SignOutResult> => {
        const { error } = await supabase.auth.signOut()
        return {
            error: error?.message ?? null,
        }
    }, [])

    const value = useMemo<AuthContextValue>(
        () => ({
            session,
            user: session?.user ?? null,
            loading,
            signIn,
            signUp,
            signOut,
        }),
        [session, loading, signIn, signUp],
    )

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
