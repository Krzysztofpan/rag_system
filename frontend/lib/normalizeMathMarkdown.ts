const LATEX_COMMAND = /\\(?:text|textrm|mathrm|mathbf|times|cdot|frac|sum|prod|int|left|right|sqrt|leq|geq|neq|approx|infty|alpha|beta|gamma|delta|theta|lambda|pi|sigma|omega|to)\b/

function prepareMath(inner: string): string {
    return inner.trim().replace(/(?<=[A-Za-z0-9])_(?=[A-Za-z0-9])/g, '\\_')
}

function toDisplayMath(inner: string): string {
    return `$$\n${prepareMath(inner)}\n$$`
}

export function normalizeMathMarkdown(content: string): string {
    return content
        .replace(/\\\[([\s\S]*?)\\\]/g, (_match, inner: string) => toDisplayMath(inner))
        .replace(/\\\(([\s\S]*?)\\\)/g, (_match, inner: string) => `$${prepareMath(inner)}$`)
        .replace(/(?<!\\)\[([^[\]]+)](?!\()/g, (match, inner: string) => {
            if (!LATEX_COMMAND.test(inner)) {
                return match
            }

            return toDisplayMath(inner)
        })
}
