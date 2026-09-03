import { type Dispatch, type SetStateAction, useState, useTransition } from 'react';
import { Plus, Search } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useIsMobile } from '@/hooks/use-mobile';
import useCreateConveration from '@/hooks/useCreateConversation';
import { items } from '@/src/pages/ConversationPage.const';

import { Input } from '../ui/input';
import { Spinner } from '../ui/spinner';
import AvatarView from '../utils/AvatarView';

type ConversationPageHeaderProps = {
    sortMethodIndex: number | null;
    setSortMethodIndex: Dispatch<SetStateAction<number | null>>;
    searchValue: string;
    setSearchValue: Dispatch<SetStateAction<string>>;
}


const ConversationsPageHeader = ({ sortMethodIndex, setSortMethodIndex, searchValue, setSearchValue }: ConversationPageHeaderProps) => {
    const [searchMode, setSearchMode] = useState(false)
    const { mutate: createConversation } = useCreateConveration()
    const [pending, startTransition] = useTransition()
    const isMobile = useIsMobile()
    const handleAddConversation = () => {
        startTransition(() => {
            createConversation()

            return
        })
    }

    return (
        <div className="flex justify-end">
            {!searchMode
                ? (
                        <div className="flex items-center gap-4 w-full">
                            <Button onClick={() => setSearchMode(true)} variant="outline" className="py-5 rounded-full aspect-square">
                                <Search />
                            </Button>
                            <Select items={items} value={sortMethodIndex} onValueChange={setSortMethodIndex}>
                                <SelectTrigger className="w-[180px] shrink-1 py-5 rounded-full truncate">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectGroup>
                                        {items.map((item) => (
                                            <SelectItem key={item.value} value={item.value}>
                                                {item.label}
                                            </SelectItem>
                                        ))}
                                    </SelectGroup>
                                </SelectContent>
                            </Select>
                            <Button className={`flex gap-2 px-7 py-5 rounded-full cursor-pointer ${isMobile && 'px-0 py-4 aspect-square'}`} onClick={handleAddConversation}>
                                {pending ? <Spinner /> : <Plus />}
                                {' '}
                                {!isMobile && (
                                    pending ? 'Adding conversation' : 'Add New'
                                )}
                            </Button>
                            <AvatarView />
                        </div>
                    )
                : (
                        <div className="flex gap-4 w-full items-center relative">
                            <Input value={searchValue} onChange={(e) => setSearchValue(e.target.value)} className="py-5 flex-1 rounded-full pl-15" placeholder="Search by conversation title" />
                            <Button
                                variant="ghost"
                                className="py-5 md:px-4 cursor-pointer"
                                onClick={() => {
                                    setSearchMode(false)
                                    setSearchValue('')
                                }}
                            >
                                Cancel
                            </Button>
                            <Search className="absolute scale-75 left-5" />
                        </div>
                    )}
        </div>
    );
}

export default ConversationsPageHeader;
