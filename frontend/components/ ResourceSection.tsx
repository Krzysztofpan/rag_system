"use client"

import { SidebarTrigger, useSidebar } from "@/components/ui/sidebar"
import UploadFilePage from "./UploadFile"
import { Separator } from "./ui/separator"
import { useOptimistic, useState, useTransition } from "react"
import ResourceItem from "./ResourceItem"
import { createPendingResource, uploadResource } from "@/lib/api"
import type { Resource } from "@/types/resource"

const conversationId = "e682d642-6295-40f7-b20c-1f16fe1dcc78"

function ResourceSection() {
  const { state } = useSidebar()
  const [resources, setResources] = useState<Resource[]>([])
  const [optimisticResources, addOptimisticResource] = useOptimistic<Resource[], Resource>(resources, (currentResources, newResource) => [...currentResources, newResource])
  const [, startTransition] = useTransition()

  const isCollapsed = state === "collapsed"

  const handleSelectResource = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const pendingResource = createPendingResource(file)

    startTransition(async () => {
      addOptimisticResource(pendingResource)
      const uploadedResource = await uploadResource(pendingResource, conversationId)
      setResources((currentResources) => [...currentResources, uploadedResource])
    })
  }

  return (
    <aside className={`flex h-full shrink-0 flex-col overflow-hidden rounded-xl bg-sidebar text-sidebar-foreground ring-1 ring-sidebar-border transition-[width] duration-200 ease-linear ${isCollapsed ? "w-(--sidebar-width-icon)" : "w-(--sidebar-width)"}`}>
      <div className={`flex h-12 shrink-0 items-center gap-2 px-2 ${isCollapsed ? "justify-center" : "justify-between pl-4"}`}>
        {!isCollapsed && <span className='truncate font-medium'>Źródła</span>}
        <SidebarTrigger />
      </div>
      <Separator />
      <div className={`min-h-0 flex-1 overflow-y-auto flex flex-col py-4 ${isCollapsed ? "items-center gap-2" : "px-7 gap-6"}`}>
        <UploadFilePage handleSelectResource={handleSelectResource} />
        <div>
          <div className={`flex flex-col ${isCollapsed ? "items-center" : ""}`}>
            {optimisticResources.map((resource) => (
              <ResourceItem key={resource.id} resource={resource} />
            ))}
          </div>
        </div>
      </div>
    </aside>
  )
}

export default ResourceSection
