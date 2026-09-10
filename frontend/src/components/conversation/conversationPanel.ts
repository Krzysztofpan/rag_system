import { type ClassValue } from 'clsx'

import { cn } from '@/lib/utils'

export function conversationPanelClassName(...classes: ClassValue[]) {
    return cn(
        'flex h-full min-h-0 shrink-0 flex-col overflow-hidden bg-sidebar text-sidebar-foreground',
        'max-md:w-full max-md:flex-1',
        'md:rounded-xl md:ring-1 md:ring-sidebar-border md:transition-[width] md:duration-200 md:ease-linear',
        ...classes,
    )
}
