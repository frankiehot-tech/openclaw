export interface CodeBlockProps {
  code: string
  language?: string
  showLineNumbers?: boolean
  className?: string
}

export function CodeBlock({
  code,
  language,
  showLineNumbers = false,
  className,
}: CodeBlockProps) {
  const lines = code.split('\n')

  return (
    <div
      className={`bg-bg-200 border border-border-100 rounded-md overflow-hidden my-3 font-mono ${className ?? ''}`}
    >
      {(language || showLineNumbers) && (
        <div className="flex items-center justify-between px-3.5 py-2 bg-bg-300 border-b border-border-100 text-[11px] text-text-400 font-mono">
          {language ? <span>{language}</span> : <span />}
        </div>
      )}
      <pre className="p-3.5 m-0 text-[13px] leading-relaxed overflow-x-auto text-text-100">
        <code>
          {showLineNumbers
            ? lines.map((line, i) => (
                <span key={i} className="block">
                  <span className="inline-block w-8 text-right mr-4 text-text-500 select-none">
                    {i + 1}
                  </span>
                  {line || '\u00A0'}
                </span>
              ))
            : code}
        </code>
      </pre>
    </div>
  )
}
