import { EllipsisVertical, type LucideIcon } from 'lucide-react'

import { useSidebar } from '@/components/ui/sidebar'
import { formatDate } from '@/lib/date'

type ResourceItemProps = {
    title: string;
    icon: LucideIcon;
    createdAt: string;
    type: string;
    onOpen: () => void;
}

const ResourceItem = ({ title, icon: Icon, createdAt, onOpen }: ResourceItemProps) => {
    const { state } = useSidebar()
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
                                <EllipsisVertical size={18} />
                            </div>
                        </>
                    )
                : null}
        </div>
    )
}

export default ResourceItem
