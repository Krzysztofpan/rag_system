import Markdown from 'react-markdown'
import rehypeKatex from 'rehype-katex'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'

import { citationIndexFromHref, remarkCitations, sourceByIndex } from '@/lib/citations'
import { isHeadingLabelParagraph, isSectionOutlineList } from '@/lib/markdownHeadings'
import { normalizeMathMarkdown } from '@/lib/normalizeMathMarkdown'
import { cn } from '@/lib/utils'
import type { MessageSource } from '@/types/citation'

import MessageCitation from './messageCitation/MessageCitation'

import 'katex/dist/katex.min.css'

type MarkdownContentProps = {
    content: string;
    className?: string;
    conversationId?: string;
    sources?: MessageSource[];
}

const MarkdownContent = ({
    content,
    className,
    conversationId,
    sources,
}: MarkdownContentProps) => {
    return (
        <div className={cn('prose-chat max-w-none wrap-break-word', className)}>
            <Markdown
                remarkPlugins={[remarkMath, remarkGfm, remarkCitations]}
                rehypePlugins={[[rehypeKatex, { strict: 'ignore' }]]}
                components={{
                    p: ({ children, node }) => (
                        <p
                            className={isHeadingLabelParagraph(node)
                                ? 'mt-8 mb-6 text-2xl font-bold first:mt-0 last:mb-0'
                                : 'mb-4 last:mb-0'}
                        >
                            {children}
                        </p>
                    ),
                    ul: ({ children }) => <ul className="mb-4 list-disc space-y-1.5 pl-6 last:mb-0">{children}</ul>,
                    ol: ({ children, node }) => (
                        <ol
                            className={isSectionOutlineList(node)
                                ? 'mt-6 mb-4 flex list-none flex-col gap-8 pl-0 last:mb-0'
                                : 'mb-4 list-decimal space-y-1.5 pl-6 last:mb-0'}
                        >
                            {children}
                        </ol>
                    ),
                    h1: ({ children }) => <h1 className="mt-8 mb-4 text-3xl font-bold first:mt-0 last:mb-0">{children}</h1>,
                    h2: ({ children }) => <h2 className="mt-8 mb-4 text-2xl font-bold first:mt-0 last:mb-0">{children}</h2>,
                    h3: ({ children }) => <h3 className="mt-6 mb-4 text-xl font-bold first:mt-0 last:mb-0">{children}</h3>,
                    strong: ({ children }) => <strong className="font-bold">{children}</strong>,
                    em: ({ children }) => <em className="italic">{children}</em>,
                    hr: () => <hr className="my-4 border-mist-400" />,
                    blockquote: ({ children }) => <blockquote className="mb-4 border-l-4 border-mist-400 pl-4 italic last:mb-0">{children}</blockquote>,
                    a: ({ href, children }) => {
                        const index = citationIndexFromHref(href)
                        if (index != null) {
                            const source = sourceByIndex(sources, index)
                            if (!source || !conversationId) {
                                return <sup className="text-muted-foreground">{`[${index}]`}</sup>
                            }
                            return (
                                <MessageCitation
                                    source={source}
                                    conversationId={conversationId}
                                    variant="inline"
                                />
                            )
                        }
                        return (
                            <a href={href} className="underline underline-offset-2 hover:opacity-80" target="_blank" rel="noopener noreferrer">
                                {children}
                            </a>
                        )
                    },
                    pre: ({ children }) => <pre className="mb-4 overflow-x-auto rounded-xl bg-mist-300 p-4 text-sm last:mb-0">{children}</pre>,
                    code: ({ className, children, ...props }) => {
                        const isBlock = Boolean(className?.includes('language-'))

                        if (isBlock) {
                            return (
                                <code className={cn('block font-mono text-sm', className)} {...props}>
                                    {children}
                                </code>
                            )
                        }

                        return (
                            <code className="rounded-md bg-mist-300 px-1.5 py-0.5 font-mono text-sm" {...props}>
                                {children}
                            </code>
                        )
                    },
                    table: ({ children }) => (
                        <div className="mb-4 overflow-x-auto last:mb-0">
                            <table className="w-full border-collapse text-sm">{children}</table>
                        </div>
                    ),
                    thead: ({ children }) => <thead className="bg-mist-300">{children}</thead>,
                    th: ({ children }) => <th className="border border-mist-400 px-3 py-2 text-left font-semibold">{children}</th>,
                    td: ({ children }) => <td className="border border-mist-400 px-3 py-2">{children}</td>,
                }}
            >
                {normalizeMathMarkdown(content)}
            </Markdown>
        </div>
    )
}

export default MarkdownContent
