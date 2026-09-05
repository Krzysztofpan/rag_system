import { ArrowRight, type LucideIcon } from 'lucide-react'
import type { CSSProperties } from 'react'

import { Button } from '@/components/ui/button'
import { useSidebar } from '@/components/ui/sidebar';

type CreateResourceItemTypeProps = {
    displayName: string;
    type: string;
    icon: LucideIcon;
    color: string;
}

const CreateResourceItemType = ({ displayName, icon: Icon, color }: CreateResourceItemTypeProps) => {
    const { state } = useSidebar()
    const isCollapsed = state === 'collapsed'


    return (
        <Button variant="ghost" style={{ '--resource-color': color } as CSSProperties} className="flex rounded-full gap-1 text-amber-100 justify-between cursor-pointer h-auto p-2 bg-(--resource-color) hover:bg-[color-mix(in_srgb,var(--resource-color),black_20%)]">
            <div className="text-xs flex flex-col gap-1 items-start">
                <Icon />
                {!isCollapsed && <span>{displayName}</span>}
            </div>
            {!isCollapsed && <ArrowRight />}

        </Button>
    )
}

export default CreateResourceItemType
