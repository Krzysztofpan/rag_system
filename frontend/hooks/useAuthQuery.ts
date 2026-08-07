import {
    useQuery,
    type UseQueryOptions,
    type UseQueryResult,
} from '@tanstack/react-query'

import { useAuth } from '@/contexts/auth/AuthContext'
import { userQueryKey } from '@/lib/queryKeys'

type AuthQueryOptions<
    TQueryFnData = unknown,
    TError = Error,
    TData = TQueryFnData,
> = Omit<
    UseQueryOptions<TQueryFnData, TError, TData>,
    'queryKey'
> & {
    queryKey: readonly unknown[];
}

export function useAuthQuery<
    TQueryFnData = unknown,
    TError = Error,
    TData = TQueryFnData,
>(
    options: AuthQueryOptions<TQueryFnData, TError, TData>,
): UseQueryResult<TData, TError> {
    const { user } = useAuth()
    const { queryKey, enabled, ...rest } = options

    return useQuery({
        ...rest,
        queryKey: user
            ? userQueryKey(user.id, ...queryKey)
            : ['auth-query-disabled', ...queryKey],
        enabled: !!user && (enabled ?? true),
    })
}
