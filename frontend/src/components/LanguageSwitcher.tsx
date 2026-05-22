import { useI18nStore, type Language } from "@/i18n"

const options: { value: Language; native: string }[] = [
  { value: "zh-CN", native: "简体中文" },
  { value: "en", native: "English" },
]

export default function LanguageSwitcher({ className }: { className?: string }) {
  const language = useI18nStore((s) => s.language)
  const loading = useI18nStore((s) => s.loading)
  const setLanguage = useI18nStore((s) => s.setLanguage)

  return (
    <div className={className}>
      <select
        value={language}
        disabled={loading}
        onChange={(e) => void setLanguage(e.target.value as Language)}
        className="bg-transparent text-foreground outline-none disabled:opacity-50"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.native}
          </option>
        ))}
      </select>
    </div>
  )
}
