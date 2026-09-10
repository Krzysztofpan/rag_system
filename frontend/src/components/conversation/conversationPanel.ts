import { type ClassValue } from 'clsx'

import { cn } from '@/lib/utils'

export function conversationPanelClassName(...classes: ClassValue[]) {
    return cn(
        'flex h-full min-h-0 shrink-0 flex-col overflow-hidden bg-sidebar text-sidebar-foreground',
        'rounded-xl ring-1 ring-sidebar-border transition-[width] duration-200 ease-linear',
        'max-md:w-full max-md:flex-1 max-md:rounded-none max-md:ring-0',
        ...classes,
    )
}
