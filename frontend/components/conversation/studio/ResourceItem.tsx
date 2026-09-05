import { EllipsisVertical } from 'lucide-react';
import { type LucideIcon } from 'lucide-react'

import { useSidebar } from '@/components/ui/sidebar';

type ResourceItem = {
    title: string;
    icon: LucideIcon;
    createdAt: string;
    type: string;
}

const ResourceItem = ({ title, icon: Icon, createdAt }: ResourceItem) => {
    const { state } = useSidebar()
    const isCollapsed = state === 'collapsed'

    return (
        <div className={`flex gap-4 items-center cursor-pointer ${isCollapsed ? 'aspect-square p-1 justify-center m-auto' : 'px-3 py-2'}  hover:bg-foreground/10 rounded-xl`}>
            <div>
                <Icon />
            </div>
            {!isCollapsed
                ? (
                        <>
                            <div className="flex-1 text-sm flex flex-col">
                                <span className="font-bold">{title}</span>
                                <span className="text-muted-foreground">{createdAt}</span>
                            </div>
                            <div>
                                <EllipsisVertical size={18} />
                            </div>
                        </>
                    )
                : null}
        </div>
    );
}

export default ResourceItem;
