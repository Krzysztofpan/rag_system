import docxIcon from '@/src/assets/icons/docx-icon.png'
import mdIcon from '@/src/assets/icons/md-icon.png'
import pdfIcon from '@/src/assets/icons/pdf-icon.png'
import txtIcon from '@/src/assets/icons/txt-icon.png'

export const IconsMap: Record<string, string> = {
    'application/pdf': pdfIcon,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': docxIcon,
    'text/markdown': mdIcon,
    'text/plain': txtIcon,
}
