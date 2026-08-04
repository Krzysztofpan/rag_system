'use client'

import { SidebarTrigger, useSidebar } from '@/components/ui/sidebar'
import { useResources, useResourcesClient } from '@/hooks/useResources'

import { Separator } from './ui/separator'
import { Skeleton } from './ui/skeleton'
import ResourceItem from './ResourceItem'
import UploadFilePage from './UploadFile'

const conversationId = 'f77a3288-7589-49d5-bd12-3a29597d3b0a'
const SKELETON_COUNT = 3

function ResourceItemSkeleton({ isCollapsed }: { isCollapsed: boolean }) {
    return (
        <div className={`flex gap-2 items-center p-3 py-4 ${isCollapsed ? 'justify-center' : 'w-full'}`}>
            <Skeleton className="size-6.25 shrink-0 rounded" />
            {!isCollapsed && <Skeleton className="h-4 w-3/4" />}
        </div>
    )
}

function ResourceSection() {
    const { state } = useSidebar()
    const { data: resources = [], isLoading, error } = useResources(conversationId)
    const { uploadResource } = useResourcesClient(conversationId)

    const isCollapsed = state === 'collapsed'

    const handleSelectResource = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return
        void uploadResource(file)
    }

    return (
        <aside className={`flex h-full shrink-0 flex-col overflow-hidden rounded-xl bg-sidebar text-sidebar-foreground ring-1 ring-sidebar-border transition-[width] duration-200 ease-linear ${isCollapsed ? 'w-(--sidebar-width-icon)' : 'w-(--sidebar-width)'}`}>
            <div className={`flex h-12 shrink-0 items-center gap-2 px-2 ${isCollapsed ? 'justify-center' : 'justify-between pl-4'}`}>
                {!isCollapsed && <span className="truncate font-medium">Sources</span>}
                <SidebarTrigger />
            </div>
            <Separator />
            <div className={`min-h-0 flex-1 overflow-y-auto flex flex-col py-4 ${isCollapsed ? 'items-center gap-2' : 'px-7 gap-6'}`}>
                <UploadFilePage handleSelectResource={handleSelectResource} />
                <div>
                    <div className={`flex flex-col ${isCollapsed ? 'items-center' : ''}`}>
                        {isLoading && Array.from({ length: SKELETON_COUNT }, (_, i) => <ResourceItemSkeleton key={i} isCollapsed={isCollapsed} />)}
                        {error && !isCollapsed && <p className="px-3 py-4 text-sm text-muted-foreground">Failed to load sources. Please try again later.</p>}
                        {!isLoading && !error && resources.map((resource) => <ResourceItem key={resource.id} resource={resource} />)}
                    </div>
                </div>
            </div>
        </aside>
    )
}

export default ResourceSection
