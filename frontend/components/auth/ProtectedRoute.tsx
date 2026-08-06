import { Navigate, Outlet } from 'react-router'

import { useAuth } from '@/contexts/auth/AuthContext'

export function ProtectedRoute() {
    const { session, loading } = useAuth()

    if (loading) {
        return <div className="flex min-h-svh items-center justify-center text-sm text-muted-foreground">Loading…</div>
    }

    if (!session) {
        return <Navigate to="/login" replace />
    }

    return <Outlet />
}
