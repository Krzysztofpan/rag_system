import { ArrowRight, type LucideIcon } from 'lucide-react'
import type { CSSProperties, ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { useSidebar } from '@/components/ui/sidebar'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

type CreateResourceItemTypeProps = {
    displayName: string;
    type: string;
    icon: LucideIcon;
    color: string;
    unavailable: boolean;
}

const UnavailableContainer = ({ children }: { children: ReactNode }) => (
    <Tooltip>
        <TooltipTrigger delay={0} render={<span />}>
            {children}
        </TooltipTrigger>
        <TooltipContent side="bottom">
            Currently unavailable
        </TooltipContent>
    </Tooltip>
)

const CreateResourceItemType = ({ displayName, icon: Icon, color, unavailable }: CreateResourceItemTypeProps) => {
    const { state } = useSidebar()
    const isCollapsed = state === 'collapsed'

    const createResourceButton = (
        <Button
            disabled={unavailable}
            variant="ghost"
            style={{ '--resource-color': color } as CSSProperties}
            className={`flex ${isCollapsed ? 'rounded-full' : ''} w-full gap-1 text-amber-100 justify-between cursor-pointer h-auto p-2 bg-(--resource-color) hover:bg-[color-mix(in_srgb,var(--resource-color),black_20%)]`}
        >
            <div className="text-xs flex flex-col gap-1 items-start">
                <Icon />
                {!isCollapsed && <span>{displayName}</span>}
            </div>
            {!isCollapsed && <ArrowRight />}
        </Button>
    )

    if (unavailable) {
        return (
            <UnavailableContainer>
                {createResourceButton}
            </UnavailableContainer>
        )
    }

    return createResourceButton
}

export default CreateResourceItemType
