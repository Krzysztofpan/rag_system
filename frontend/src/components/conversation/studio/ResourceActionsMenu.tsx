import { FilePlus, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { useDeleteResource } from '@/hooks/useDeleteResource'
import { useSourcesClient } from '@/hooks/useSources'

type ResourceActionsMenuProps = {
    resourceId: string;
    title: string;
    canConvertToSource: boolean;
    onClose: () => void;
}

const ResourceActionsMenu = ({
    resourceId,
    title,
    canConvertToSource,
    onClose,
}: ResourceActionsMenuProps) => {
    const { conversationId } = useConversationContext()
    const { mutate: deleteResource } = useDeleteResource(conversationId)
    const { convertNoteToSource } = useSourcesClient(conversationId)

    return (
        <>
            <Button
                className="justify-start"
                variant="ghost"
                disabled={!canConvertToSource}
                title={canConvertToSource ? undefined : 'Note has no content'}
                onClick={() => {
                    onClose()
                    void convertNoteToSource(resourceId, `${title}.md`)
                }}
            >
                <FilePlus />
                Convert to source
            </Button>
            <Button
                className="justify-start"
                variant="ghost"
                onClick={() => {
                    onClose()
                    deleteResource(resourceId)
                }}
            >
                <Trash2 />
                Delete resource
            </Button>
        </>
    )
}

export default ResourceActionsMenu
