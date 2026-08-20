'use client'

import { SidebarTrigger, useSidebar } from '@/components/ui/sidebar'
import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { useSourcesClient } from '@/hooks/useSources'

import { Checkbox } from '../ui/checkbox'
import { Separator } from '../ui/separator'
import { Skeleton } from '../ui/skeleton'
import SourceItem from './SourceItem'
import UploadFilePage from './UploadFile'

const SKELETON_COUNT = 3

function SourceItemSkeleton({ isCollapsed }: { isCollapsed: boolean }) {
    return (
        <div className={`flex gap-2 items-center p-3 py-4 ${isCollapsed ? 'justify-center' : 'w-full'}`}>
            <Skeleton className="size-6.25 shrink-0 rounded" />
            {!isCollapsed && <Skeleton className="h-4 w-3/4" />}
        </div>
    )
}

function SourceSection() {
    const { state } = useSidebar()
    const {
        conversationId,
        handleToogleSelectAllSources,
        unselectedSourcesIds: unselectedIds,
        sourcesResponseObject: { data: sources = [], isLoading, error },
    } = useConversationContext()
    const { uploadSource } = useSourcesClient(conversationId)

    const isCollapsed = state === 'collapsed'

    const handleSelectSource = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return
        void uploadSource(file)
    }

    return (
        <aside className={`flex h-full shrink-0 flex-col overflow-hidden rounded-xl bg-sidebar text-sidebar-foreground ring-1 ring-sidebar-border transition-[width] duration-200 ease-linear ${isCollapsed ? 'w-(--sidebar-width-icon)' : 'w-(--sidebar-width)'}`}>
            <div className={`flex h-12 shrink-0 items-center gap-2 px-2 ${isCollapsed ? 'justify-center' : 'justify-between pl-4'}`}>
                {!isCollapsed && <span className="truncate font-medium">Sources</span>}
                <SidebarTrigger />
            </div>
            <Separator />
            <div className={`min-h-0 flex-1 overflow-y-auto flex flex-col py-4 ${isCollapsed ? 'items-center gap-2' : 'px-7 gap-6'}`}>
                <UploadFilePage handleSelectSource={handleSelectSource} />

                <div>
                    {!isLoading && !error && sources.length > 0
                        ? (
                                <div className="flex justify-end text-sm gap-6 px-3">
                                    Select all
                                    {' '}
                                    <Checkbox checked={!unselectedIds.length} onCheckedChange={handleToogleSelectAllSources} />
                                </div>
                            )
                        : (
                                <div className="text-center text-muted-foreground text-sm">
                                    Select your first source
                                </div>
                            )}
                    <div className={`flex flex-col ${isCollapsed ? 'items-center' : ''}`}>
                        {isLoading && Array.from({ length: SKELETON_COUNT }, (_, i) => <SourceItemSkeleton key={i} isCollapsed={isCollapsed} />)}
                        {error && !isCollapsed && <p className="px-3 py-4 text-sm text-muted-foreground">Failed to load sources. Please try again later.</p>}
                        {!isLoading && !error && sources.map((source) => <SourceItem key={source.id} source={source} />)}
                    </div>
                </div>
            </div>
        </aside>
    )
}

export default SourceSection
