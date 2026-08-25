import {
    PopoverDescription,
    PopoverHeader,
    PopoverTitle,
} from '@/components/ui/popover'
import { Spinner } from '@/components/ui/spinner'
import { useCitationPreview } from '@/hooks/useCitationPreview'
import type { DocumentMessageSource } from '@/types/citation'

type DocumentCitationContentProps = {
    conversationId: string;
    source: DocumentMessageSource;
    isOpen: boolean;
}

const DocumentCitationContent = ({
    conversationId,
    source,
    isOpen,
}: DocumentCitationContentProps) => {
    const preview = useCitationPreview(conversationId, source, isOpen)

    if (preview.isPending) {
        return (
            <div className="flex items-center gap-2 text-muted-foreground">
                <Spinner />
                Wczytywanie…
            </div>
        )
    }

    if (preview.isError) {
        return <p className="text-destructive">Nie udało się wczytać źródła.</p>
    }

    if (!preview.data) {
        return null
    }

    return (
        <>
            <PopoverHeader>
                <PopoverTitle>{preview.data.title}</PopoverTitle>
            </PopoverHeader>
            <PopoverDescription className="max-h-64 overflow-y-auto whitespace-pre-wrap text-foreground">
                {preview.data.body}
            </PopoverDescription>
        </>
    )
}

export default DocumentCitationContent
