import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { authService } from '../services/api'
import { useAuthStore } from '../store/useAuthStore'
import { useThemeStore } from '../store/useThemeStore'
import { Loader2, Lock, User, Sun, Moon, Check, Globe2 } from 'lucide-react'

// 登录成功动画组件
const LoginSuccessAnimation = ({ onComplete }: { onComplete: () => void }) => {
  useEffect(() => {
    const timer = setTimeout(onComplete, 2000)
    return () => clearTimeout(timer)
  }, [onComplete])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-white/90 dark:bg-[#111827]/88 backdrop-blur-md"
    >
      <div className="flex flex-col items-center">
        {/* 圆环进度动画 */}
        <div className="relative w-24 h-24">
          {/* 背景圆环 */}
          <svg className="w-24 h-24 transform -rotate-90">
            <circle
              cx="48"
              cy="48"
              r="44"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
              className="text-slate-200 dark:text-slate-700"
            />
            {/* 进度圆环 - 绿色渐变 */}
            <motion.circle
              cx="48"
              cy="48"
              r="44"
              stroke="url(#successGradient)"
              strokeWidth="4"
              fill="none"
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1, ease: "easeInOut" }}
              style={{
                strokeDasharray: "276.46",
                strokeDashoffset: "0"
              }}
            />
            <defs>
              <linearGradient id="successGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#22C55E" />
                <stop offset="100%" stopColor="#10B981" />
              </linearGradient>
            </defs>
          </svg>
          
          {/* 中心对勾 */}
          <motion.div
            className="absolute inset-0 flex items-center justify-center"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.8, duration: 0.4, type: "spring", stiffness: 200 }}
          >
            <div className="w-12 h-12 rounded-full bg-gradient-to-r from-green-500 to-emerald-500 flex items-center justify-center shadow-lg">
              <Check className="w-7 h-7 text-white" strokeWidth={3} />
            </div>
          </motion.div>
        </div>

        {/* 成功文字 */}
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1, duration: 0.3 }}
          className="mt-6 text-lg font-medium text-slate-700 dark:text-slate-200"
        >
          登录成功
        </motion.p>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.3 }}
          className="mt-2 text-sm text-slate-500 dark:text-slate-400"
        >
          正在跳转...
        </motion.p>
      </div>
    </motion.div>
  )
}

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [focusedField, setFocusedField] = useState<string | null>(null)
  const [showSuccess, setShowSuccess] = useState(false)
  
  const navigate = useNavigate()
  const { setToken, setUser } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()
  
  // 初始化主题
  useEffect(() => {
    const savedTheme = useThemeStore.getState().theme
    document.documentElement.classList.toggle('dark', savedTheme === 'dark')
  }, [])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await authService.login({ username, password })
      setToken(response.access_token, response.refresh_token)
      
      const user = await authService.getCurrentUser()
      setUser(user)
      
      // 显示成功动画
      setShowSuccess(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || '登录失败，请检查用户名和密码')
      setLoading(false)
    }
  }

  const handleAnimationComplete = () => {
    navigate('/chat')
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-6 py-10">
      {/* 登录成功动画 */}
      <AnimatePresence>
        {showSuccess && <LoginSuccessAnimation onComplete={handleAnimationComplete} />}
      </AnimatePresence>

      <motion.button
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.3, duration: 0.3 }}
        onClick={toggleTheme}
        className="fixed right-6 top-6 z-50 rounded-xl border border-black/5 bg-white/90 p-3 shadow-sm transition-all duration-200 hover:bg-white dark:border-white/8 dark:bg-[#162031]/92 dark:hover:bg-[#1d2940]"
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
        title={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
      >
        <motion.div
          initial={false}
          animate={{ rotate: theme === 'dark' ? 180 : 0 }}
          transition={{ duration: 0.3 }}
        >
          {theme === 'dark' ? (
            <Sun className="h-5 w-5 text-yellow-500" />
          ) : (
            <Moon className="h-5 w-5 text-slate-700" />
          )}
        </motion.div>
      </motion.button>

      {/* 登录卡片 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-[460px]"
      >
        <div className="relative overflow-hidden rounded-[28px] border border-black/5 bg-white/94 shadow-[0_16px_40px_rgba(15,23,42,0.06)] dark:border-white/8 dark:bg-[#111827]/96">
          <div className="p-8">
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.5 }}
              className="text-center mb-8"
            >
              <div className="inline-flex items-center gap-2 text-primary">
                <Globe2 className="h-5 w-5" />
                <span className="text-[13px] font-semibold">Geo-Agent</span>
              </div>
              <h1 className="mb-2 mt-5 text-[28px] font-semibold text-foreground">
                Geo-Agent
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                登录后继续进入研究工作区
              </p>
            </motion.div>

            {/* 表单 */}
            <form onSubmit={handleLogin} className="space-y-5">
              {/* 用户名输入框 */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3, duration: 0.5 }}
              >
                <label htmlFor="username" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  用户名/邮箱
                </label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <User className={`h-5 w-5 transition-colors duration-200 ${
                      focusedField === 'username' 
                        ? 'text-blue-500 dark:text-blue-400' 
                        : 'text-slate-400 dark:text-slate-500'
                    }`} />
                  </div>
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    onFocus={() => setFocusedField('username')}
                    onBlur={() => setFocusedField(null)}
                    placeholder="请输入用户名或邮箱"
                    required
                    disabled={loading || showSuccess}
                    className="w-full rounded-2xl border border-slate-200 bg-[#f7f9fc] py-3 pl-10 pr-4 text-slate-900 transition-all duration-200 placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:shadow-lg focus:shadow-blue-500/10 hover:border-slate-300 disabled:opacity-50 dark:border-white/10 dark:bg-[#162031] dark:text-slate-100 dark:focus:bg-[#1a2538] dark:hover:border-white/15"
                  />
                  {/* 聚焦时的发光效果 */}
                  {focusedField === 'username' && (
                    <motion.div
                      layoutId="inputGlow"
                      className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500/20 to-indigo-500/20 -z-10 blur-xl"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                </div>
              </motion.div>

              {/* 密码输入框 */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4, duration: 0.5 }}
              >
                <label htmlFor="password" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  密码
                </label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className={`h-5 w-5 transition-colors duration-200 ${
                      focusedField === 'password' 
                        ? 'text-blue-500 dark:text-blue-400' 
                        : 'text-slate-400 dark:text-slate-500'
                    }`} />
                  </div>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onFocus={() => setFocusedField('password')}
                    onBlur={() => setFocusedField(null)}
                    placeholder="请输入密码"
                    required
                    disabled={loading || showSuccess}
                    className="w-full rounded-2xl border border-slate-200 bg-[#f7f9fc] py-3 pl-10 pr-4 text-slate-900 transition-all duration-200 placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:shadow-lg focus:shadow-blue-500/10 hover:border-slate-300 disabled:opacity-50 dark:border-white/10 dark:bg-[#162031] dark:text-slate-100 dark:focus:bg-[#1a2538] dark:hover:border-white/15"
                  />
                  {/* 聚焦时的发光效果 */}
                  {focusedField === 'password' && (
                    <motion.div
                      layoutId="inputGlow"
                      className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500/20 to-indigo-500/20 -z-10 blur-xl"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                </div>
              </motion.div>
              
              {/* 错误提示 */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl"
                  >
                    <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                  </motion.div>
                )}
              </AnimatePresence>
              
              {/* 登录按钮 */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5, duration: 0.5 }}
              >
                <motion.button
                  type="submit"
                  disabled={loading || showSuccess}
                  whileHover={{ scale: loading || showSuccess ? 1 : 1.02 }}
                  whileTap={{ scale: loading || showSuccess ? 1 : 0.98 }}
                  className="relative w-full overflow-hidden rounded-2xl bg-primary px-4 py-3 font-medium text-white shadow-lg shadow-blue-500/20 transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100 group hover:bg-primary/90"
                >
                  {/* 按钮高光效果 */}
                  <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000" />
                  
                  <span className="relative flex items-center justify-center gap-2">
                    {loading && <Loader2 className="h-5 w-5 animate-spin" />}
                    {loading ? '登录中...' : '登录'}
                  </span>
                </motion.button>
              </motion.div>
            </form>

            {/* 注册链接 */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6, duration: 0.5 }}
              className="mt-6 text-center"
            >
              <p className="text-sm text-slate-600 dark:text-slate-400">
                还没有账号？{' '}
                <Link 
                  to="/register" 
                  className="relative font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors duration-200 group"
                >
                  立即注册
                  <span className="absolute left-0 bottom-0 w-0 h-0.5 bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400 group-hover:w-full transition-all duration-300" />
                </Link>
              </p>
            </motion.div>
          </div>
        </div>

      </motion.div>
    </div>
  )
}
