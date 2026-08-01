import { useState } from 'react'
import { EllipsisVertical, Pencil, Trash2 } from 'lucide-react'

import { IconsMap } from '@/types/IconsMap'
import type { Resource } from '@/types/resource'

import { Button } from './ui/button'
import { Checkbox } from './ui/checkbox'
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover'
import { useSidebar } from './ui/sidebar'
import { Spinner } from './ui/spinner'

type ResourceItemProps = {
    resource: Resource;
}

const ResourceItem = ({ resource }: ResourceItemProps) => {
    const { file, status, error } = resource
    const { state } = useSidebar()
    const [isOpen, setIsOpen] = useState(false)

    const isCollapsed = state === 'collapsed'
    const isPending = status === 'pending'

    return (
        <div
            title={error ?? undefined}
            className={
                `flex gap-2 items-center group hover:bg-muted p-3 py-4 rounded-lg cursor-pointer
        ${isCollapsed ? 'justify-center' : 'w-full justify-between'} ${status === 'rejected' || isPending ? 'opacity-60' : ''}  
        `
            }
        >
            <div className="flex gap-2 items-center min-w-0">
                <img src={IconsMap[file.type]} width={25} alt={file.name} />
                {!isCollapsed && <div className="flex items-center text-sm truncate w-full">{file.name}</div>}
            </div>
            {status === 'pending'
                ? (
                        <Spinner />
                    )
                : (
                        <div className={`${isCollapsed ? 'hidden' : 'flex'} gap-2 items-center`}>
                            <Popover onOpenChange={setIsOpen}>
                                <PopoverTrigger className={`${isOpen ? 'block' : 'hidden'} group-hover:block p-0 m-0 flex justify-center items-center cursor-pointer`}>
                                    <EllipsisVertical size={18} />
                                </PopoverTrigger>
                                <PopoverContent side="bottom" align="start" className={`${isOpen ? 'flex' : 'hidden'} w-56 flex-col  gap-0 p-0`}>
                                    <Button className="p-5 flex gap-2 justify-start cursor-pointer" variant="ghost">
                                        <Trash2 />
                                        Delete resource
                                    </Button>
                                    <Button className="p-5 flex gap-2 justify-start cursor-pointer" variant="ghost">
                                        <Pencil />
                                        Change name of resource
                                    </Button>
                                </PopoverContent>
                            </Popover>
                            {!isCollapsed && <Checkbox />}
                        </div>
                    )}
        </div>
    )
}

export default ResourceItem
