import type { MessageSource } from '@/types/Message'

const CITE_HREF = /^#cite-(\d+)$/
const CITE_MARKER = /\[(\d+)\]/g

type MarkdownNode = {
    type: string;
    value?: string;
    url?: string;
    children?: MarkdownNode[];
}

const SKIPPED_PARENT_TYPES = new Set([
    'code',
    'inlineCode',
    'link',
    'linkReference',
])

export function citationIndexFromHref(href: string | undefined): number | null {
    if (!href) {
        return null
    }
    const match = href.match(CITE_HREF)
    return match ? Number(match[1]) : null
}

function citationNodes(value: string): MarkdownNode[] {
    const nodes: MarkdownNode[] = []
    let offset = 0

    for (const match of value.matchAll(CITE_MARKER)) {
        const index = match.index
        if (index > offset) {
            nodes.push({ type: 'text', value: value.slice(offset, index) })
        }
        const citationIndex = match[1]
        nodes.push({
            type: 'link',
            url: `#cite-${citationIndex}`,
            children: [{ type: 'text', value: `[${citationIndex}]` }],
        })
        offset = index + match[0].length
    }

    if (offset < value.length) {
        nodes.push({ type: 'text', value: value.slice(offset) })
    }
    return nodes
}

function transformCitations(node: MarkdownNode): void {
    if (!node.children || SKIPPED_PARENT_TYPES.has(node.type)) {
        return
    }

    const transformed: MarkdownNode[] = []
    for (const child of node.children) {
        if (child.type === 'text' && child.value?.match(CITE_MARKER)) {
            transformed.push(...citationNodes(child.value))
            continue
        }
        transformCitations(child)
        transformed.push(child)
    }
    node.children = transformed
}

export function remarkCitations() {
    return (tree: MarkdownNode): void => {
        transformCitations(tree)
    }
}

export function sourceByIndex(
    sources: MessageSource[] | undefined,
    index: number,
): MessageSource | undefined {
    return sources?.find((source) => source.index === index)
}

export function webArticleTitle(source: MessageSource): string {
    if (source.kind !== 'web') {
        return ''
    }
    const title = (source.title ?? '').trim()
    return title && title !== source.url ? title : ''
}

