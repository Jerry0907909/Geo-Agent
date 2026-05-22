// ---- Zustand-based i18n store with lazy-loading ----
import { create } from "zustand"
import type { Language, TranslationDict, TransKey } from "./types"

const STORAGE_KEY = "geo-agent-lang"

function detectBrowserLanguage(): Language {
  try {
    const nav = navigator.language || (navigator as any).userLanguage || ""
    if (nav.startsWith("zh")) return "zh-CN"
  } catch {}
  return "en"
}

function getInitialLanguage(): Language {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === "zh-CN" || saved === "en") return saved
  } catch {}
  return detectBrowserLanguage()
}

interface I18nStore {
  language: Language
  translations: TranslationDict | null
  loading: boolean
  error: string | null
  setLanguage: (lang: Language) => Promise<void>
  t: (key: TransKey | string, params?: Record<string, string | number>) => string
  init: () => Promise<void>
  fmtDate: (date: Date | number, options?: Intl.DateTimeFormatOptions) => string
  fmtNumber: (n: number, options?: Intl.NumberFormatOptions) => string
}

// Lazy-load locale modules — only the active language is loaded
const localeCache: Record<Language, TranslationDict | null> = { en: null, "zh-CN": null }

async function loadLocale(lang: Language): Promise<TranslationDict> {
  if (localeCache[lang]) return localeCache[lang]!
  const mod: { default: TranslationDict } = await import(`./locales/${lang}.ts`)
  localeCache[lang] = mod.default
  return mod.default
}

// Preload en (fallback) immediately
loadLocale("en").catch(() => {})

export const useI18nStore = create<I18nStore>((set, get) => ({
  language: getInitialLanguage(),
  translations: null,
  loading: false,
  error: null,

  async setLanguage(lang: Language) {
    const current = get().language
    if (current === lang) return

    set({ loading: true, error: null })
    try {
      localStorage.setItem(STORAGE_KEY, lang)
      await loadLocale(lang)
    } catch {
      localStorage.setItem(STORAGE_KEY, "en")
    }
    window.location.reload()
  },

  t(key: TransKey | string, params?: Record<string, string | number>) {
    const { translations } = get()
    const def = key // fallback to key itself
    if (!translations) return def

    const [section, field] = key.split(".") as [keyof TranslationDict, string]
    const table = translations[section]
    if (!table) { console.warn(`[i18n] Missing section: ${section}`); return def }

    const val = (table as any)[field]
    if (typeof val !== "string") { console.warn(`[i18n] Missing key: ${key}`); return def }

    if (!params) return val
    // Simple interpolation: {key} → value
    return val.replace(/\{(\w+)\}/g, (_, k: string) => String(params[k] ?? `{${k}}`))
  },

  async init() {
    const lang = get().language
    set({ loading: true })
    try {
      const translations = await loadLocale(lang)
      set({ translations, loading: false })
    } catch {
      const translations = await loadLocale("en")
      set({ language: "en", translations, loading: false })
    }
  },

  fmtDate(date: Date | number, options?: Intl.DateTimeFormatOptions) {
    const loc = get().language === "zh-CN" ? "zh-CN" : "en-US"
    return new Intl.DateTimeFormat(loc, options ?? { dateStyle: "medium" }).format(date)
  },

  fmtNumber(n: number, options?: Intl.NumberFormatOptions) {
    const loc = get().language === "zh-CN" ? "zh-CN" : "en-US"
    return new Intl.NumberFormat(loc, options).format(n)
  },
}))
