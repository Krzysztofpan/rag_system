import { DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'

const AddSourceHeader = () => (
    <DialogHeader className="pr-8">
        <div className="pointer-events-none absolute -top-16 left-8 size-40 rounded-full bg-violet-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -top-10 right-8 size-40 rounded-full bg-emerald-500/20 blur-3xl" />
        <DialogTitle className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Add sources
            <span className="mt-1 block bg-gradient-to-r from-violet-400 via-sky-400 to-emerald-400 bg-clip-text font-semibold text-transparent">from files or links</span>
        </DialogTitle>
        <DialogDescription className="sr-only">Paste a YouTube link or drop a file to add it to this conversation.</DialogDescription>
    </DialogHeader>
)

export default AddSourceHeader
