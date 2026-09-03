import { Fragment, useState } from 'react'
import { Plus } from 'lucide-react'

import { Button } from '../../ui/button'
import { Dialog, DialogContent, DialogTrigger } from '../../ui/dialog'
import { useSidebar } from '../../ui/sidebar'
import AddSourceHeader from './addSource/AddSourceHeader'
import FileDropzone from './addSource/FileDropzone'
import YoutubeUrlForm from './addSource/YoutubeUrlForm'

type UploadFileBtn = {
    handleSelectSource: (file: File) => void;
    handleAddYoutubeUrl: (url: string) => void;
}

const UploadFilePage = ({ handleSelectSource, handleAddYoutubeUrl }: UploadFileBtn) => {
    const { state } = useSidebar()
    const isCollapsed = state === 'collapsed'
    const [open, setOpen] = useState(false)

    const close = () => setOpen(false)

    return (
        <div className={`flex flex-col gap-2 ${isCollapsed ? 'items-center' : ''}`}>
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogTrigger render={<Button variant="outline" size={isCollapsed ? 'icon' : 'default'} title="Add source" className={isCollapsed ? '' : 'w-full rounded-full font-medium'} />}>
                    <Plus />
                    {!isCollapsed && 'Add source'}
                </DialogTrigger>
                <DialogContent className="gap-6 overflow-hidden rounded-2xl p-6 sm:max-w-2xl sm:p-8">
                    <AddSourceHeader />
                    <Fragment key={String(open)}>
                        <YoutubeUrlForm
                            onAdd={(url) => {
                                handleAddYoutubeUrl(url)
                                close()
                            }}
                        />
                        <FileDropzone
                            onFile={(file) => {
                                handleSelectSource(file)
                                close()
                            }}
                        />
                    </Fragment>
                </DialogContent>
            </Dialog>
        </div>
    )
}

export default UploadFilePage
