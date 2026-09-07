import { useState } from 'react'
import { EllipsisVertical, type LucideIcon } from 'lucide-react'

import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useSidebar } from '@/components/ui/sidebar'
import { formatDate } from '@/lib/date'

import ResourceActionsMenu from './ResourceActionsMenu'

type ResourceItemProps = {
    id: string;
    title: string;
    icon: LucideIcon;
    createdAt: string;
    onOpen: () => void;
}

const ResourceItem = ({ id, title, icon: Icon, createdAt, onOpen }: ResourceItemProps) => {
    const { state } = useSidebar()
    const [isMenuOpen, setIsMenuOpen] = useState(false)
    const isCollapsed = state === 'collapsed'

    const formattedCreatedAt = formatDate(createdAt, {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
    })

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
                                <span className="font-bold">{title}</span>
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
                                            resourceId={id}
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
