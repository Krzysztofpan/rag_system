import { useState } from 'react'

import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import type { MessageSource } from '@/types/citation'

import CitationPopoverBody from './CitationPopoverBody'

type MessageCitationProps = {
    source: MessageSource;
    conversationId: string;
    variant?: 'inline' | 'chip';
}

const MessageCitation = ({
    source,
    conversationId,
    variant = 'inline',
}: MessageCitationProps) => {
    const [isOpen, setIsOpen] = useState(false)

    return (
        <Popover onOpenChange={setIsOpen}>
            <PopoverTrigger
                className={cn(
                    'cursor-pointer align-super text-xs font-semibold text-primary underline-offset-2 hover:underline',
                    variant === 'chip' && 'inline-flex h-6 items-center rounded-full bg-mist-300 px-2 align-middle no-underline',
                )}
                aria-label={`Źródło ${source.index}`}
            >
                {source.index}
            </PopoverTrigger>
            <PopoverContent align="start" className="w-80 max-w-[min(20rem,calc(100vw-2rem))]">
                <CitationPopoverBody
                    source={source}
                    conversationId={conversationId}
                    isOpen={isOpen}
                />
            </PopoverContent>
        </Popover>
    )
}

export default MessageCitation
