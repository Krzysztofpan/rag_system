type HastLike = {
    type: string;
    tagName?: string;
    value?: string;
    children?: HastLike[];
}

const COLON_OR_SPACE = /^[\s:]+$/

function significantChildren(node: HastLike | undefined): HastLike[] {
    return (node?.children ?? []).filter((child) => {
        if (child.type !== 'text') {
            return true
        }
        return Boolean(child.value && child.value.trim() !== '')
    })
}

function nodeText(node: HastLike | undefined): string {
    if (!node) {
        return ''
    }
    if (node.type === 'text') {
        return node.value ?? ''
    }
    return significantChildren(node).map(nodeText).join('')
}

export function isHeadingLabelParagraph(node: HastLike | undefined): boolean {
    if (node?.tagName !== 'p') {
        return false
    }

    const children = significantChildren(node)
    if (children.length === 0) {
        return false
    }

    const hasStrong = children.some((child) => child.tagName === 'strong')
    if (!hasStrong) {
        return false
    }

    const labelOnly = children.every((child) => {
        if (child.tagName === 'strong') {
            return true
        }
        return child.type === 'text' && COLON_OR_SPACE.test(child.value ?? '')
    })
    if (!labelOnly) {
        return false
    }

    const text = nodeText(node).trim()
    return text.endsWith(':') || text.length <= 80
}

export function isHeadingLikeListItem(node: HastLike | undefined): boolean {
    if (node?.tagName !== 'li') {
        return false
    }

    const [first, ...rest] = significantChildren(node)
    return isHeadingLabelParagraph(first) && rest.length > 0
}

export function isSectionOutlineList(node: HastLike | undefined): boolean {
    if (node?.tagName !== 'ol') {
        return false
    }

    const items = significantChildren(node).filter((child) => child.tagName === 'li')
    return items.length > 0 && items.every(isHeadingLikeListItem)
}
