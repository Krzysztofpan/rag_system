import type { MessageSource } from '@/types/citation'

import DocumentCitationContent from './DocumentCitationContent'
import WebCitationContent from './WebCitationContent'

type CitationPopoverBodyProps = {
    source: MessageSource;
    conversationId: string;
    isOpen: boolean;
}

const CitationPopoverBody = ({
    source,
    conversationId,
    isOpen,
}: CitationPopoverBodyProps) => {
    if (source.kind === 'web') {
        return <WebCitationContent source={source} />
    }

    return (
        <DocumentCitationContent
            conversationId={conversationId}
            source={source}
            isOpen={isOpen}
        />
    )
}

export default CitationPopoverBody
