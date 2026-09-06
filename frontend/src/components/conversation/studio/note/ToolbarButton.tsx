import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

type ToolbarButtonProps = {
    label: string;
    active?: boolean;
    disabled?: boolean;
    onClick: () => void;
    children: ReactNode;
}

export default function ToolbarButton({
    label,
    active,
    disabled,
    onClick,
    children,
}: ToolbarButtonProps) {
    return (
        <Tooltip>
            <TooltipTrigger
                delay={200}
                render={(
                    <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        disabled={disabled}
                        aria-label={label}
                        aria-pressed={active}
                        onClick={onClick}
                        className={cn(
                            'text-muted-foreground',
                            active && 'bg-muted text-foreground',
                        )}
                    />
                )}
            >
                {children}
            </TooltipTrigger>
            <TooltipContent side="bottom">{label}</TooltipContent>
        </Tooltip>
    )
}
