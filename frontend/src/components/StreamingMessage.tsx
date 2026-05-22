/**
 * StreamingMessage — 实时 Markdown 流式输出 + AI cursor
 */

import { useMemo } from "react"
import Markdown from "react-markdown"
import { cn } from "@/lib/utils"

interface Props {
  content: string
  isStreaming?: boolean
  className?: string
}

export default function StreamingMessage({ content, isStreaming = false, className }: Props) {
  const markdownComponents = useMemo(
    () => ({
      p: ({ children }: any) => <p className="mb-3 last:mb-0 leading-7">{children}</p>,
      ul: ({ children }: any) => <ul className="mb-3 list-disc space-y-1 pl-5">{children}</ul>,
      ol: ({ children }: any) => <ol className="mb-3 list-decimal space-y-1 pl-5">{children}</ol>,
      li: ({ children }: any) => <li className="leading-7">{children}</li>,
      code: ({ inline, children, ...props }: any) =>
        inline ? (
          <code className="rounded-md bg-secondary/70 px-1.5 py-0.5 text-[0.9em]" {...props}>{children}</code>
        ) : (
          <code className="mb-3 block overflow-x-auto rounded-xl border border-border/50 bg-secondary/40 px-4 py-3 text-[0.85em]" {...props}>{children}</code>
        ),
    }),
    [],
  )

  if (!content) return null

  return (
    <div className={cn("relative leading-7", className)}>
      <Markdown components={markdownComponents}>{content || " "}</Markdown>
      {isStreaming && (
        <span
          className="ml-0.5 inline-block h-[1.2em] w-[2px] translate-y-[0.1em] rounded-full bg-primary/55 align-baseline"
          style={{ animation: "sm-cursor 1.8s ease-in-out infinite" }}
        />
      )}
      <style>{`
        @keyframes sm-cursor {
          0%, 100% { opacity: 0.25; transform: translateY(0.1em) scaleY(0.6); }
          50% { opacity: 0.9; transform: translateY(0.1em) scaleY(1.2); }
        }
        @media (prefers-reduced-motion: reduce) {
          span[style*="sm-cursor"] { animation: none; opacity: 0.4; }
        }
      `}</style>
    </div>
  )
}
