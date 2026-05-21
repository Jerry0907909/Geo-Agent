import { useEffect, useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { AnimatePresence, motion } from "framer-motion"
import { Check, Loader2, Moon, Sun, Mail, ArrowRight } from "lucide-react"
import { authService } from "../services/api"
import { useAuthStore } from "../store/useAuthStore"
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

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default function LoginPage() {
  const [mode, setMode] = useState<"password" | "code">("password")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [verificationCode, setVerificationCode] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [sendingCode, setSendingCode] = useState(false)
  const [countdown, setCountdown] = useState(0)

  const navigate = useNavigate()
  const { setToken, setUser } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark")
  }, [theme])

  useEffect(() => {
    if (!success) return
    const timer = setTimeout(() => navigate("/chat"), 1000)
    return () => clearTimeout(timer)
  }, [success, navigate])

  useEffect(() => {
    if (countdown <= 0) return
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [countdown])

  const handleSendCode = async () => {
    const email = username.trim()
    if (!EMAIL_REGEX.test(email)) {
      setError("请输入邮箱地址")
      return
    }
    setError("")
    setSendingCode(true)
    try {
      await authService.sendVerificationCode(email)
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

    if (mode === "code") {
      if (verificationCode.length !== 6) {
        setError("请输入 6 位验证码")
        return
      }
    } else {
      if (!password) {
        setError("请输入密码")
        return
      }
    }

    setLoading(true)
    try {
      const payload: any = { username }
      if (mode === "code") {
        payload.verification_code = verificationCode
      } else {
        payload.password = password
      }

      const resp = await authService.login(payload)
      setToken(resp.access_token, resp.refresh_token)
      const user = await authService.getCurrentUser()
      setUser(user)
      setSuccess(true)
    } catch (err: any) {
      setError(extractError(err))
      setLoading(false)
    }
  }

  if (success) {
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
          <p className="text-lg font-medium">已登录</p>
          <p className="text-sm text-muted-foreground">正在进入工作区</p>
        </motion.div>
      </div>
    )
  }

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
            <h1 className="text-2xl font-semibold tracking-tight">欢迎回来</h1>
            <p className="text-sm text-muted-foreground">登录你的 Geo-Agent 账号</p>
          </div>

          {/* Mode tabs */}
          <div className="flex rounded-xl bg-secondary p-1">
            {[
              { key: "password" as const, label: "密码登录" },
              { key: "code" as const, label: "验证码登录" },
            ].map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => { setMode(key); setError("") }}
                className={`flex-1 rounded-[10px] py-2 text-sm font-medium transition-all duration-200 ${
                  mode === key
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="login-email" className="text-sm font-medium">
                账号
              </label>
              <Input
                id="login-email"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={mode === "code" ? "输入邮箱地址" : "输入用户名或邮箱"}
                disabled={loading}
                autoComplete={mode === "code" ? "email" : "username"}
                required
              />
            </div>

            {mode === "password" ? (
              <div className="space-y-2">
                <label htmlFor="login-password" className="text-sm font-medium">
                  密码
                </label>
                <Input
                  id="login-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="输入密码"
                  disabled={loading}
                  autoComplete="current-password"
                  required
                />
              </div>
            ) : (
              <div className="space-y-2">
                <label htmlFor="login-code" className="text-sm font-medium">
                  验证码
                </label>
                <div className="flex gap-2">
                  <Input
                    id="login-code"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value)}
                    placeholder="6 位数字验证码"
                    maxLength={6}
                    disabled={loading}
                    autoComplete="one-time-code"
                    className="flex-1"
                    required
                  />
                  <Button
                    type="button"
                    variant="outline"
                    disabled={sendingCode || countdown > 0 || !EMAIL_REGEX.test(username.trim())}
                    onClick={handleSendCode}
                    className="shrink-0 gap-1.5"
                  >
                    {sendingCode ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Mail className="h-3.5 w-3.5" />
                    )}
                    {countdown > 0 ? `${countdown}s` : "发送"}
                  </Button>
                </div>
              </div>
            )}

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
              登录
              {!loading && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>

          {/* Footer link */}
          <p className="text-center text-sm text-muted-foreground">
            还没有账号？{" "}
            <Link to="/register" className="font-medium text-primary hover:underline underline-offset-2">
              创建账号
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  )
}
