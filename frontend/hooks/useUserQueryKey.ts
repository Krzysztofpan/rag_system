import { useAuth } from '@/contexts/auth/AuthContext'
import { userQueryKey } from '@/lib/queryKeys'

export function useUserQueryKey(...keys: readonly unknown[]) {
    const { user } = useAuth()

    if (!user) {
        throw new Error('useUserQueryKey requires an authenticated user')
    }

    return userQueryKey(user.id, ...keys)
}
