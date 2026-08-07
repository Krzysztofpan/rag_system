export function userQueryKey(userId: string, ...keys: readonly unknown[]) {
    return [userId, ...keys] as const
}
