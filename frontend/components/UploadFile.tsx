import { useRef } from "react"
import { Button } from "./ui/button"

import { Plus } from "lucide-react"
import { useSidebar } from "./ui/sidebar"


type UploadFileBtn = {
  handleSelectResource: (e: React.ChangeEvent<HTMLInputElement>) => void
}

const UploadFilePage = ({handleSelectResource}: UploadFileBtn) => {
  const fileRef = useRef<HTMLInputElement>(null)
  const { state } = useSidebar()
  const isCollapsed = state === "collapsed"

  const handleClick = () => {
    fileRef.current?.click()
  }

  return (
    <div className={`flex flex-col gap-4 ${isCollapsed ? "items-center" : ""}`}>
      <Button
        onClick={handleClick}
        variant='outline'
        size={isCollapsed ? "icon" : "default"}
        title='Add resource'
        className={isCollapsed ? "" : "w-full rounded-full font-medium"}
      >
        <Plus />
        {!isCollapsed && "Add resource"}
      </Button>
      <input type='file' accept='.pdf,.docxs,.txt,.md' className='hidden' ref={fileRef} onChange={handleSelectResource} />
    </div>
  )
}

export default UploadFilePage
