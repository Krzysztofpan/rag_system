import { NotepadText } from 'lucide-react';

import { useSidebar } from '@/components/ui/sidebar';

import ResourceItem from './ResourceItem';


const ResourcesSection = () => {
    const { state } = useSidebar()
    const isCollapsed = state === 'collapsed'


    const resources = [
        { title: 'New note', icon: NotepadText, createdAt: 'today', type: 'note' },
    ]


    return (
        <div className={`${isCollapsed ? '' : 'px-5 '} py-3 flex flex-col gap-4`}>
            {resources.map((resource) => (
                <ResourceItem
                    {...resource}
                />
            ))}
        </div>
    );
}

export default ResourcesSection;
