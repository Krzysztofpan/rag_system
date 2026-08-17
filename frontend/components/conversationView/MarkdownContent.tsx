import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { cn } from '@/lib/utils'

type MarkdownContentProps = {
    content: string;
    className?: string;
}

const MarkdownContent = ({ content, className }: MarkdownContentProps) => {
    return (
        <div className={cn('prose-chat max-w-none wrap-break-word', className)}>
            <Markdown
                remarkPlugins={[remarkGfm]}
                components={{
                    p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
                    ul: ({ children }) => <ul className="mb-4 list-disc space-y-1 pl-6 last:mb-0">{children}</ul>,
                    ol: ({ children }) => <ol className="mb-4 list-decimal space-y-1 pl-6 last:mb-0">{children}</ol>,
                    li: ({ children }) => <li className="last:pb-4">{children}</li>,
                    h1: ({ children }) => <h1 className="mb-4 text-xl font-bold last:mb-0">{children}</h1>,
                    h2: ({ children }) => <h2 className="mb-3 text-lg font-bold last:mb-0">{children}</h2>,
                    h3: ({ children }) => <h3 className="mb-2 text-base font-bold last:mb-0">{children}</h3>,
                    strong: ({ children }) => (
                        <strong className="font-bold text-xl">
                            {children}
                            {' '}
                            <br />
                        </strong>
                    ),
                    em: ({ children }) => <em className="italic">{children}</em>,
                    hr: () => <hr className="my-4 border-mist-400" />,
                    blockquote: ({ children }) => <blockquote className="mb-4 border-l-4 border-mist-400 pl-4 italic last:mb-0">{children}</blockquote>,
                    a: ({ href, children }) => (
                        <a href={href} className="underline underline-offset-2 hover:opacity-80" target="_blank" rel="noopener noreferrer">
                            {children}
                        </a>
                    ),
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
                {content}
            </Markdown>
        </div>
    )
}

export default MarkdownContent
