import { type CSSProperties, type ReactNode, useState } from 'react'

import { SidebarProvider } from '@/components/ui/sidebar'
import { useIsMobile } from '@/hooks/use-mobile'

function CustomSidebarProvider({ children }: { children: ReactNode }) {
    const isMobile = useIsMobile()
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)

    return (
        <SidebarProvider
            className="contents"
            style={
                {
                    '--sidebar-width': '21vw',
                } as CSSProperties
            }
            open={!isMobile && isSidebarOpen}
            onOpenChange={setIsSidebarOpen}
        >
            {children}
        </SidebarProvider>
    )
}

export default CustomSidebarProvider
