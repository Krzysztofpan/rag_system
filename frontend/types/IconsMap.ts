import docxIcon from '@/src/assets/icons/docx-icon.png'
import jpegIcon from '@/src/assets/icons/jpeg-icon.png'
import jpgIcon from '@/src/assets/icons/jpg-icon.png'
import mdIcon from '@/src/assets/icons/md-icon.png'
import pdfIcon from '@/src/assets/icons/pdf-icon.png'
import pngIcon from '@/src/assets/icons/png-icon.png'
import txtIcon from '@/src/assets/icons/txt-icon.png'

export const IconsMap: Record<string, string> = {
    'application/pdf': pdfIcon,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': docxIcon,
    'text/markdown': mdIcon,
    'text/plain': txtIcon,
    'image/png': pngIcon,
    'image/jpeg': jpegIcon,
    'image/jpg': jpgIcon,
}

const SUFFIX_ICONS: Record<string, string> = {
    png: pngIcon,
    jpg: jpgIcon,
    jpeg: jpegIcon,
}

export function sourceIconSrc(
    contentType?: string | null,
    filename?: string | null,
): string | undefined {
    const suffix = filename?.split('.').pop()?.toLowerCase()
    if (suffix && SUFFIX_ICONS[suffix]) {
        return SUFFIX_ICONS[suffix]
    }
    return contentType ? IconsMap[contentType] : undefined
}
