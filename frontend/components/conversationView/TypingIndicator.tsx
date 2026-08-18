const TypingIndicator = () => {
    return (
        <div className="flex w-full px-3 py-3" role="status" aria-label="Assistant is typing">
            <div className="flex items-center gap-1.5">
                {[0, 1, 2].map((delayMs) => (
                    <span
                        key={delayMs}
                        className="size-2 rounded-full bg-muted-foreground animate-typing-dot [animation-fill-mode:both]"
                        style={{ animationDelay: `${delayMs * 160}ms` }}
                    />
                ))}
            </div>
        </div>
    )
}

export default TypingIndicator
