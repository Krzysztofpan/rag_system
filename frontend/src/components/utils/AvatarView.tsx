'use client'

import {
    Avatar,
    AvatarFallback,
    AvatarImage,
} from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/contexts/auth/AuthContext'

function AvatarView() {
    const { signOut } = useAuth()

    return (
        <DropdownMenu>
            <DropdownMenuTrigger render={(
                <Button variant="ghost" size="icon" className="rounded-full">
                    <Avatar>
                        <AvatarImage src="https://github.com/defaultAvatar.png" alt="avatar" />
                        <AvatarFallback>CN</AvatarFallback>
                    </Avatar>
                </Button>
            )}
            />
            <DropdownMenuContent className="w-32">
                <DropdownMenuItem variant="destructive" onClick={signOut}>Log out</DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    )
}

export default AvatarView
