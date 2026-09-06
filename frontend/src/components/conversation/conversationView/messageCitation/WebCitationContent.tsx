import {
    PopoverHeader,
    PopoverTitle,
} from '@/components/ui/popover'
import { webArticleTitle } from '@/lib/citations'
import type { WebMessageSource } from '@/types/citation'

const WebCitationContent = ({ source }: { source: WebMessageSource }) => {
    const articleTitle = webArticleTitle(source)

    return (
        <>
            {articleTitle && (
                <PopoverHeader>
                    <PopoverTitle>{articleTitle}</PopoverTitle>
                </PopoverHeader>
            )}
            <a
                href={source.url}
                className="break-all underline underline-offset-2"
                target="_blank"
                rel="noopener noreferrer"
            >
                {source.url}
            </a>
        </>
    )
}

export default WebCitationContent
