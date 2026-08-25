import { useState } from 'react'

import {
    Popover,
    PopoverContent,
    PopoverDescription,
    PopoverHeader,
    PopoverTitle,
    PopoverTrigger,
} from '@/components/ui/popover'
import { Spinner } from '@/components/ui/spinner'
import { useCitationPreview } from '@/hooks/useCitationPreview'
import { webArticleTitle } from '@/lib/citations'
import { cn } from '@/lib/utils'
import type { MessageSource } from '@/types/Message'

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
    const isWeb = source.kind === 'web'
    const preview = useCitationPreview(conversationId, source, isOpen && !isWeb)
    const articleTitle = webArticleTitle(source)

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
                {isWeb
                    ? (
                            <>
                                {articleTitle
                                    ? (
                                            <PopoverHeader>
                                                <PopoverTitle>{articleTitle}</PopoverTitle>
                                            </PopoverHeader>
                                        )
                                    : null}
                                <a
                                    href={source.url}
                                    className="break-all underline underline-offset-2"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    {source.url}
                                </a>
                            </>
                        )
                    : (
                            <>
                                {preview.isPending
                                    ? (
                                            <div className="flex items-center gap-2 text-muted-foreground">
                                                <Spinner />
                                                Wczytywanie…
                                            </div>
                                        )
                                    : null}
                                {preview.isError
                                    ? <p className="text-destructive">Nie udało się wczytać źródła.</p>
                                    : null}
                                {preview.data
                                    ? (
                                            <>
                                                <PopoverHeader>
                                                    <PopoverTitle>{preview.data.title}</PopoverTitle>
                                                </PopoverHeader>
                                                <PopoverDescription className="max-h-64 overflow-y-auto whitespace-pre-wrap text-foreground">
                                                    {preview.data.body}
                                                </PopoverDescription>
                                            </>
                                        )
                                    : null}
                            </>
                        )}
            </PopoverContent>
        </Popover>
    )
}

export default MessageCitation
