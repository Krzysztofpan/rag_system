import { Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { useDeleteResource } from '@/hooks/useDeleteResource'

type ResourceActionsMenuProps = {
    resourceId: string;
    onClose: () => void;
}

const ResourceActionsMenu = ({ resourceId, onClose }: ResourceActionsMenuProps) => {
    const { conversationId } = useConversationContext()
    const { mutate: deleteResource } = useDeleteResource(conversationId)

    return (
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
    )
}

export default ResourceActionsMenu
