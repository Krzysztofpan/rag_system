import { Button } from '../../ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../ui/dialog'
import { Input } from '../../ui/input'

type RenameSourceDialogProps = {
    filename: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSave: (name: string) => void;
}

const RenameSourceDialog = ({ filename, open, onOpenChange, onSave }: RenameSourceDialogProps) => {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <form
                    className="flex flex-col gap-4"
                    onSubmit={(e) => {
                        e.preventDefault()
                        const formData = new FormData(e.currentTarget)
                        const newName = (formData.get('name') as string).trim()
                        if (newName) {
                            onSave(newName)
                        }
                        onOpenChange(false)
                    }}
                >
                    <DialogHeader>
                        <DialogTitle>Change name of source</DialogTitle>
                        <DialogDescription>Enter a new name for this source.</DialogDescription>
                    </DialogHeader>
                    <Input key={filename} name="name" defaultValue={filename} maxLength={50} autoFocus />
                    <DialogFooter>
                        <Button type="submit">Save</Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    )
}

export default RenameSourceDialog
