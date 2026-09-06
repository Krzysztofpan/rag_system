import { BellRing, Brain, type LucideIcon } from 'lucide-react'
import { ChartNetwork, NotepadText } from 'lucide-react'


export type ResourceItem = {
    name: string;
    type: string;
    icon: LucideIcon;
    color: string;
}

export const ResourceIconMap: Record<string, LucideIcon> = {
    note: NotepadText,
    mind_map: ChartNetwork,
}

export const resourcesItems: ResourceItem[] = [
    { name: 'Mind map', type: 'mind-map', icon: Brain, color: '#975435' },
    { name: 'somehting else', type: 'something-else', icon: BellRing, color: '#879664' },
]
