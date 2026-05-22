import type { TransKey } from "./types"

/** Map backend SSE status text (Chinese) to i18n keys. */
const EXACT_STATUS_KEYS: Record<string, TransKey> = {
  "正在生成回答...": "chat.generating",
  "正在检索文献...": "chat.searching",
  "正在思考": "chat.thinking",
  "正在分析图像...": "chat.analyzingImage",
  "正在搜索网络信息...": "chat.searchingWeb",
  "图片分析失败，使用文本模式...": "chat.imageAnalysisFallback",
  "正在规划搜索策略...": "chat.planningSearch",
  "正在语义召回最相关内容...": "chat.recallingContent",
  "正在重排序...": "chat.reranking",
}

type TranslateFn = (key: TransKey, params?: Record<string, string | number>) => string

export function translateStreamStatus(message: string, t: TranslateFn): string {
  const raw = message.trim()
  if (!raw) return ""

  const exactKey = EXACT_STATUS_KEYS[raw]
  if (exactKey) return t(exactKey)

  if (raw.startsWith("当前模型:")) {
    return t("chat.currentModel", { info: raw.replace(/^当前模型:\s*/, "") })
  }

  const searchQueryMatch = raw.match(/^正在搜索\s+(\d+)\s+个\s*query/)
  if (searchQueryMatch) {
    return t("chat.searchingQueries", { count: searchQueryMatch[1] })
  }

  const readPageMatch = raw.match(/^正在读取\s+(\d+)\s+个网页/)
  if (readPageMatch) {
    return t("chat.readingPages", { count: readPageMatch[1] })
  }

  const analyzeImagesMatch = raw.match(/^正在分析\s+(\d+)\s+张文档图片/)
  if (analyzeImagesMatch) {
    return t("chat.analyzingDocImages", { count: analyzeImagesMatch[1] })
  }

  return raw
}
