/** Detect dialogue language from user question and assistant answer (content-based). */

const CJK_RE = /[\u4e00-\u9fff]/g
const LATIN_RE = /[a-zA-Z]/g

export function isChineseText(text: string): boolean {
  const trimmed = text.trim()
  if (!trimmed) return false
  const cjk = trimmed.match(CJK_RE)?.length ?? 0
  if (cjk >= 2) return true
  const latin = trimmed.match(LATIN_RE)?.length ?? 0
  return cjk >= 1 && latin < cjk * 2
}

export function conversationLanguage(question: string, answer: string): "en" | "zh" {
  const q = question.trim()
  const a = answer.trim()
  if (isChineseText(q)) return "zh"
  if (isChineseText(a) && q.length < 24) return "zh"
  const sample = `${q} ${a.slice(0, 500)}`
  const cjk = sample.match(CJK_RE)?.length ?? 0
  const latin = sample.match(LATIN_RE)?.length ?? 0
  if (cjk >= 4 && cjk >= latin * 0.2) return "zh"
  return "en"
}
