import { useEffect, useMemo, useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useI18nStore } from "@/i18n"
import { motion, AnimatePresence } from "framer-motion"
import { Check, Loader2, Moon, Sun, Mail, ArrowRight } from "lucide-react"
import { authService } from "../services/api"
import { useThemeStore } from "../store/useThemeStore"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

function extractError(err: any): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === "string") return detail
  if (Array.isArray(detail)) {
    return detail.map((d: any) => `${(d.loc || []).join(".")}: ${d.msg}`).join("；")
  }
  return "Request failed"
}

export default function RegisterPage() {
  const t = useI18nStore((s) => s.t)
  useI18nStore((s) => s.language) // BUG-2: trigger re-render
  const [formData, setFormData] = useState({ username: "", email: "", password: "", confirmPassword: "", full_name: "", verificationCode: "" })
  const [step, setStep] = useState<"form" | "success">("form")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [sendingCode, setSendingCode] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const navigate = useNavigate()
  const { theme, toggleTheme } = useThemeStore()

  useEffect(() => { document.documentElement.classList.toggle("dark", theme === "dark") }, [theme])
  useEffect(() => { if (step !== "success") return; const timer = setTimeout(() => navigate("/login"), 1200); return () => clearTimeout(timer) }, [step, navigate])
  useEffect(() => { if (countdown <= 0) return; const timer = setTimeout(() => setCountdown((c) => c - 1), 1000); return () => clearTimeout(timer) }, [countdown])

  const validation = useMemo(() => ({
    username: formData.username.trim().length >= 3,
    email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email),
    password: formData.password.length >= 6,
    confirm: formData.confirmPassword.length > 0 && formData.confirmPassword === formData.password,
    code: formData.verificationCode.length === 6,
  }), [formData])

  if (step === "success") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="flex flex-col items-center gap-4 text-center">
          <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 200, damping: 20 }} className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg">
            <Check className="h-6 w-6" />
          </motion.div>
          <p className="text-lg font-medium">{t("auth.registerSuccess")}</p>
          <p className="text-sm text-muted-foreground">{t("auth.redirecting")}</p>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-background">
      <button onClick={toggleTheme} className="fixed right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full border border-border/60 bg-card text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground">
        {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>
      <div className="mx-auto flex w-full max-w-[440px] flex-col justify-center px-6">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }} className="w-full space-y-8">
          <div className="text-center">
            <Link to="/" className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-lg font-bold text-primary-foreground shadow-sm">G</Link>
          </div>
          <div className="space-y-1.5 text-center">
            <h1 className="text-2xl font-semibold tracking-tight">{t("auth.createAccount")}</h1>
            <p className="text-sm text-muted-foreground">{t("auth.registerSubtitle")}</p>
          </div>
          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div className="space-y-1.5"><label htmlFor="reg-username" className="text-sm font-medium">{t("auth.username")}</label>
              <Input id="reg-username" value={formData.username} onChange={(e) => setFormData((p) => ({ ...p, username: e.target.value }))} placeholder="" autoComplete="username" required /></div>
            <div className="space-y-1.5"><label htmlFor="reg-email" className="text-sm font-medium">{t("auth.email")}</label>
              <div className="flex gap-2">
                <Input id="reg-email" type="email" value={formData.email} onChange={(e) => setFormData((p) => ({ ...p, email: e.target.value }))} placeholder="" autoComplete="email" className="flex-1" required />
                <Button type="button" variant="outline" disabled={sendingCode || countdown > 0 || !validation.email} onClick={handleSendCode} className="shrink-0 gap-1.5">
                  {sendingCode ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5" />}
                  {countdown > 0 ? `${countdown}s` : t("auth.sendCode")}
                </Button>
              </div></div>
            <div className="space-y-1.5"><label htmlFor="reg-code" className="text-sm font-medium">{t("auth.sendCode")}</label>
              <Input id="reg-code" value={formData.verificationCode} onChange={(e) => setFormData((p) => ({ ...p, verificationCode: e.target.value }))} maxLength={6} autoComplete="one-time-code" required /></div>
            <div className="space-y-1.5"><label htmlFor="reg-name" className="text-sm font-medium">{t("auth.name")} <span className="text-muted-foreground font-normal">({t("auth.nameOptional")})</span></label>
              <Input id="reg-name" value={formData.full_name} onChange={(e) => setFormData((p) => ({ ...p, full_name: e.target.value }))} autoComplete="name" /></div>
            <div className="space-y-1.5"><label htmlFor="reg-password" className="text-sm font-medium">{t("auth.password")}</label>
              <Input id="reg-password" type="password" value={formData.password} onChange={(e) => setFormData((p) => ({ ...p, password: e.target.value }))} autoComplete="new-password" required /></div>
            <div className="space-y-1.5"><label htmlFor="reg-confirm" className="text-sm font-medium">{t("auth.confirmPassword")}</label>
              <Input id="reg-confirm" type="password" value={formData.confirmPassword} onChange={(e) => setFormData((p) => ({ ...p, confirmPassword: e.target.value }))} autoComplete="new-password" required /></div>
            <AnimatePresence mode="wait">
              {error && <motion.div key="error" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden rounded-xl border border-destructive/30 bg-destructive/5 px-3.5 py-2.5 text-sm text-destructive">{error}</motion.div>}
            </AnimatePresence>
            <Button type="submit" className="h-11 w-full gap-2" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {t("auth.register")}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>
          <p className="text-center text-sm text-muted-foreground">
            {t("auth.hasAccount")}{" "}
            <Link to="/login" className="font-medium text-primary hover:underline underline-offset-2">{t("auth.backToLogin")}</Link>
          </p>
        </motion.div>
      </div>
    </div>
  )

  async function handleSendCode() {
    if (!validation.email) { setError("Please enter a valid email"); return }
    setError(""); setSendingCode(true)
    try { await authService.sendVerificationCode(formData.email); setCountdown(60) } catch (err: any) { setError(extractError(err)) } finally { setSendingCode(false) }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault(); setError("")
    if (!validation.username || !validation.email || !validation.password) { setError("Please complete all required fields"); return }
    if (!validation.confirm) { setError(t("settings.passwordMismatch")); return }
    if (!validation.code) { setError("Please enter the verification code"); return }
    setLoading(true)
    try {
      await authService.register({ username: formData.username, email: formData.email, password: formData.password, full_name: formData.full_name, verification_code: formData.verificationCode })
      setStep("success")
    } catch (err: any) { setError(extractError(err)) } finally { setLoading(false) }
  }
}
