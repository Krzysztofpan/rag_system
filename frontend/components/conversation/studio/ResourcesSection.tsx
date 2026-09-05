

import { useSidebar } from '@/components/ui/sidebar'
import { Skeleton } from '@/components/ui/skeleton'
import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { useResources } from '@/hooks/useResources'

import ResourceItem from './ResourceItem'
import { ResourceIconMap } from './studio.contants'

const SKELETON_COUNT = 3

function ResourceItemSkeleton({ isCollapsed }: { isCollapsed: boolean }) {
    return (
        <div
            className={`flex gap-4 items-center ${isCollapsed ? 'aspect-square p-1 justify-center m-auto' : 'px-3 py-2'}`}
            aria-hidden
        >
            <Skeleton className="size-5 shrink-0 rounded" />
            {!isCollapsed && (
                <>
                    <div className="flex-1 flex flex-col gap-1.5">
                        <Skeleton className="h-3.5 w-2/3" />
                        <Skeleton className="h-3 w-1/3" />
                    </div>
                    <Skeleton className="size-4 shrink-0 rounded" />
                </>
            )}
        </div>
    )
}

const ResourcesSection = () => {
    const { state } = useSidebar()
    const { conversationId } = useConversationContext()
    const { data, isLoading } = useResources(conversationId)
    const resources = data?.conversationResources

    const isCollapsed = state === 'collapsed'

    return (
        <div
            className={`${isCollapsed ? '' : 'px-5 '} py-3 flex flex-col gap-4`}
            aria-busy={isLoading}
            aria-label={isLoading ? 'Loading resources' : undefined}
        >
            {!isLoading
                ? resources?.map((resource) => {
                        const icon = ResourceIconMap[resource.type]
                        return (
                            <ResourceItem
                                key={resource.id}
                                icon={icon}
                                {...resource}
                            />
                        )
                    })
                : Array.from({ length: SKELETON_COUNT }, (_, i) => (
                        <ResourceItemSkeleton key={i} isCollapsed={isCollapsed} />
                    ))}
        </div>
    )
}

export default ResourcesSection
