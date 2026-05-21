import { useEffect, useMemo, useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
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
  return "请求失败，请稍后重试"
}

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
    full_name: "",
    verificationCode: "",
  })
  const [step, setStep] = useState<"form" | "success">("form")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [sendingCode, setSendingCode] = useState(false)
  const [countdown, setCountdown] = useState(0)

  const navigate = useNavigate()
  const { theme, toggleTheme } = useThemeStore()

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark")
  }, [theme])

  useEffect(() => {
    if (step !== "success") return
    const timer = setTimeout(() => navigate("/login"), 1200)
    return () => clearTimeout(timer)
  }, [step, navigate])

  useEffect(() => {
    if (countdown <= 0) return
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [countdown])

  const validation = useMemo(
    () => ({
      username: formData.username.trim().length >= 3,
      email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email),
      password: formData.password.length >= 6,
      confirm: formData.confirmPassword.length > 0 && formData.confirmPassword === formData.password,
      code: formData.verificationCode.length === 6,
    }),
    [formData]
  )

  const handleChange = (name: keyof typeof formData, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSendCode = async () => {
    if (!validation.email) {
      setError("请先填写正确的邮箱地址")
      return
    }
    setError("")
    setSendingCode(true)
    try {
      await authService.sendVerificationCode(formData.email)
      setCountdown(60)
    } catch (err: any) {
      setError(extractError(err))
    } finally {
      setSendingCode(false)
    }
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError("")

    if (!validation.username || !validation.email || !validation.password) {
      setError("请完整填写注册信息")
      return
    }
    if (!validation.confirm) {
      setError("两次输入的密码不一致")
      return
    }
    if (!validation.code) {
      setError("请输入 6 位邮箱验证码")
      return
    }

    setLoading(true)
    try {
      await authService.register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        verification_code: formData.verificationCode,
      })
      setStep("success")
    } catch (err: any) {
      setError(extractError(err))
      setLoading(false)
    }
  }

  if (step === "success") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="flex flex-col items-center gap-4 text-center"
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200, damping: 20 }}
            className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg"
          >
            <Check className="h-6 w-6" />
          </motion.div>
          <p className="text-lg font-medium">注册成功</p>
          <p className="text-sm text-muted-foreground">正在跳转到登录</p>
        </motion.div>
      </div>
    )
  }

  const fieldStates = [
    { label: "邮箱验证", done: countdown > 0 },
    { label: "账号格式", done: validation.username && validation.email },
    { label: "密码强度", done: validation.password && validation.confirm },
  ]

  return (
    <div className="flex min-h-screen bg-background">
      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        className="fixed right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full border border-border/60 bg-card text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        aria-label={theme === "dark" ? "切换浅色模式" : "切换深色模式"}
      >
        {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>

      <div className="mx-auto flex w-full max-w-[440px] flex-col justify-center px-6">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
          className="w-full space-y-8"
        >
          {/* Brand */}
          <div className="text-center">
            <Link to="/" className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-lg font-bold text-primary-foreground shadow-sm">
              G
            </Link>
          </div>

          {/* Heading */}
          <div className="space-y-1.5 text-center">
            <h1 className="text-2xl font-semibold tracking-tight">创建账号</h1>
            <p className="text-sm text-muted-foreground">加入 Geo-Agent 开始智能问答</p>
          </div>

          {/* Progress dots */}
          <div className="flex items-center justify-center gap-1.5">
            {fieldStates.map((f) => (
              <div
                key={f.label}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  f.done ? "w-8 bg-primary" : "w-8 bg-muted"
                }`}
              />
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div className="space-y-1.5">
              <label htmlFor="reg-username" className="text-sm font-medium">
                用户名
              </label>
              <Input
                id="reg-username"
                value={formData.username}
                onChange={(e) => handleChange("username", e.target.value)}
                placeholder="输入用户名"
                autoComplete="username"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="reg-email" className="text-sm font-medium">
                邮箱
              </label>
              <div className="flex gap-2">
                <Input
                  id="reg-email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleChange("email", e.target.value)}
                  placeholder="输入邮箱地址"
                  autoComplete="email"
                  className="flex-1"
                  required
                />
                <Button
                  type="button"
                  variant="outline"
                  disabled={sendingCode || countdown > 0 || !validation.email}
                  onClick={handleSendCode}
                  className="shrink-0 gap-1.5"
                >
                  {sendingCode ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Mail className="h-3.5 w-3.5" />
                  )}
                  {countdown > 0 ? `${countdown}s` : "验证"}
                </Button>
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="reg-code" className="text-sm font-medium">
                验证码
              </label>
              <Input
                id="reg-code"
                value={formData.verificationCode}
                onChange={(e) => handleChange("verificationCode", e.target.value)}
                placeholder="输入 6 位邮箱验证码"
                maxLength={6}
                autoComplete="one-time-code"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="reg-name" className="text-sm font-medium">
                姓名 <span className="text-muted-foreground font-normal">（可选）</span>
              </label>
              <Input
                id="reg-name"
                value={formData.full_name}
                onChange={(e) => handleChange("full_name", e.target.value)}
                placeholder="输入你的姓名"
                autoComplete="name"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="reg-password" className="text-sm font-medium">
                密码
              </label>
              <Input
                id="reg-password"
                type="password"
                value={formData.password}
                onChange={(e) => handleChange("password", e.target.value)}
                placeholder="至少 6 位字符"
                autoComplete="new-password"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="reg-confirm" className="text-sm font-medium">
                确认密码
              </label>
              <Input
                id="reg-confirm"
                type="password"
                value={formData.confirmPassword}
                onChange={(e) => handleChange("confirmPassword", e.target.value)}
                placeholder="再次输入密码"
                autoComplete="new-password"
                required
              />
            </div>

            <AnimatePresence mode="wait">
              {error && (
                <motion.div
                  key="error"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden rounded-xl border border-destructive/30 bg-destructive/5 px-3.5 py-2.5 text-sm text-destructive"
                >
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

            <Button type="submit" className="h-11 w-full gap-2" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              创建账号
              {!loading && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>

          {/* Footer link */}
          <p className="text-center text-sm text-muted-foreground">
            已有账号？{" "}
            <Link to="/login" className="font-medium text-primary hover:underline underline-offset-2">
              返回登录
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  )
}
