import type { CSSProperties } from 'react'

import SourceSection from '@/components/SourceSection'
import { SidebarProvider } from '@/components/ui/sidebar'

import './App.css'


function App() {
    return (
        <SidebarProvider
            className="flex h-svh flex-col overflow-hidden"
            style={
                {
                    '--sidebar-width': '25vw',
                } as CSSProperties
            }
        >
            <header className="flex h-14 shrink-0 items-center px-4">
                <h1 className="text-lg font-medium">AI Assistant</h1>
            </header>
            <div className="flex min-h-0 flex-1 gap-2 p-2 pt-0">
                <SourceSection />
                <main className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto rounded-xl ring-1 ring-sidebar-border">
                    <div>main</div>
                </main>
            </div>
        </SidebarProvider>
    )
}

export default App
