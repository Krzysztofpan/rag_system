import { useState } from 'react'
import { EllipsisVertical, type LucideIcon } from 'lucide-react'

import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useSidebar } from '@/components/ui/sidebar'
import { formatRelativeTime } from '@/lib/date'
import { noteHasContent } from '@/lib/note'
import type { Resource } from '@/services/api/types'

import ResourceActionsMenu from './ResourceActionsMenu'

type ResourceItemProps = {
    resource: Resource;
    icon: LucideIcon;
    onOpen: () => void;
}

const ResourceItem = ({ resource, icon: Icon, onOpen }: ResourceItemProps) => {
    const { state } = useSidebar()
    const [isMenuOpen, setIsMenuOpen] = useState(false)
    const isCollapsed = state === 'collapsed'

    const formattedCreatedAt = formatRelativeTime(resource.createdAt)
    const canConvertToSource = resource.type === 'note' && noteHasContent(resource.content)

    return (
        <div
            role="button"
            tabIndex={0}
            onClick={onOpen}
            onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    onOpen()
                }
            }}
            className={`flex gap-4 items-center cursor-pointer ${isCollapsed ? 'aspect-square p-1 justify-center m-auto' : 'px-3 py-2'}  hover:bg-foreground/10 rounded-xl`}
        >
            <div>
                <Icon />
            </div>
            {!isCollapsed
                ? (
                        <>
                            <div className="flex-1 text-sm flex flex-col">
                                <span className="font-bold">{resource.title}</span>
                                <span className="text-muted-foreground">{formattedCreatedAt}</span>
                            </div>
                            <div
                                onClick={(event) => event.stopPropagation()}
                                onKeyDown={(event) => event.stopPropagation()}
                            >
                                <Popover open={isMenuOpen} onOpenChange={setIsMenuOpen}>
                                    <PopoverTrigger className="m-0 flex cursor-pointer items-center justify-center p-0 text-muted-foreground hover:text-foreground">
                                        <EllipsisVertical size={18} />
                                    </PopoverTrigger>
                                    <PopoverContent side="bottom" align="end" className="w-56 gap-0 p-1">
                                        <ResourceActionsMenu
                                            resourceId={resource.id}
                                            title={resource.title}
                                            canConvertToSource={canConvertToSource}
                                            onClose={() => setIsMenuOpen(false)}
                                        />
                                    </PopoverContent>
                                </Popover>
                            </div>
                        </>
                    )
                : null}
        </div>
    )
}

export default ResourceItem
