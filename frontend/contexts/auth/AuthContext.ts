import { createContext, useContext } from 'react'
import type { Session, User } from '@supabase/supabase-js'

export type SignUpResult = {
    error: string | null;
    needsEmailConfirmation: boolean;
}

export type AuthContextValue = {
    session: Session | null;
    user: User | null;
    loading: boolean;
    signIn: (email: string, password: string) => Promise<{ error: string | null }>;
    signUp: (email: string, password: string) => Promise<SignUpResult>;
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
    const ctx = useContext(AuthContext)
    if (!ctx) {
        throw new Error('useAuth must be used within AuthProvider')
    }
    return ctx
}
