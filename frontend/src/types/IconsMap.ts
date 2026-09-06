import docxIcon from '@/assets/icons/docx-icon.png'
import jpegIcon from '@/assets/icons/jpeg-icon.png'
import jpgIcon from '@/assets/icons/jpg-icon.png'
import mdIcon from '@/assets/icons/md-icon.png'
import pdfIcon from '@/assets/icons/pdf-icon.png'
import pngIcon from '@/assets/icons/png-icon.png'
import txtIcon from '@/assets/icons/txt-icon.png'
import youtubeIcon from '@/assets/icons/youtube-icon.png'

export const IconsMap: Record<string, string> = {
    'application/pdf': pdfIcon,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': docxIcon,
    'text/markdown': mdIcon,
    'text/plain': txtIcon,
    'image/png': pngIcon,
    'image/jpeg': jpegIcon,
    'image/jpg': jpgIcon,
    'video/youtube': youtubeIcon,
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
