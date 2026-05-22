// ---- i18n entry point ----
// Usage:
//   import { useI18nStore } from "@/i18n"
//   const { t } = useI18nStore()
//   <p>{t("nav.chat")}</p>

export { useI18nStore } from "./store"
export { translateStreamStatus } from "./streamStatus"
export type { Language, TransKey } from "./types"
