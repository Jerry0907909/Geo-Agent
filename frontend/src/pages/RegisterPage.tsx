import React, { useState, useEffect, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { authService } from '../services/api'
import { useThemeStore } from '../store/useThemeStore'
import { Loader2, Sun, Moon, User, Mail, UserCircle, Lock, Check, X } from 'lucide-react'

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    full_name: ''
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [focusedField, setFocusedField] = useState<string | null>(null)
  const [touched, setTouched] = useState<Record<string, boolean>>({})
  
  const navigate = useNavigate()
  const { theme, toggleTheme } = useThemeStore()
  
  // 表单验证
  const validation = useMemo(() => {
    return {
      username: formData.username.length >= 3,
      email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email),
      password: formData.password.length >= 6,
      confirmPassword: formData.confirmPassword === formData.password && formData.confirmPassword.length > 0
    }
  }, [formData])
  
  // 初始化主题
  useEffect(() => {
    const savedTheme = useThemeStore.getState().theme
    document.documentElement.classList.toggle('dark', savedTheme === 'dark')
  }, [])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleBlur = (field: string) => {
    setTouched(prev => ({ ...prev, [field]: true }))
    setFocusedField(null)
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    if (formData.password !== formData.confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }

    setLoading(true)

    try {
      await authService.register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name
      })
      
      // 注册成功跳转到登录页
      navigate('/login')
    } catch (err: any) {
      setError(err.response?.data?.detail || '注册失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative flex items-center justify-center min-h-screen overflow-hidden">
      {/* 背景渐变 - 莫兰迪蓝色系 */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-[#0d1320] dark:via-[#111827] dark:to-[#0f1726]" />
      
      {/* 背景装饰元素 */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/4 w-96 h-96 bg-blue-200/30 dark:bg-blue-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute -bottom-1/2 -right-1/4 w-96 h-96 bg-indigo-200/30 dark:bg-indigo-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
      </div>

      {/* 主题切换按钮 */}
      <motion.button
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.3, duration: 0.3 }}
        onClick={toggleTheme}
        className="fixed top-6 right-6 z-50 rounded-full border border-slate-200 bg-white/80 p-3 shadow-lg backdrop-blur-md transition-all duration-200 hover:shadow-xl dark:border-white/8 dark:bg-[#162031]/90 dark:hover:bg-[#1d2940]"
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

      {/* 注册卡片 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-lg mx-4"
      >
        {/* 毛玻璃卡片 */}
        <div className="relative overflow-hidden rounded-2xl border border-white/20 bg-white/70 shadow-2xl backdrop-blur-xl dark:border-white/8 dark:bg-[#111827]/88">
          {/* 顶部高光 */}
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/60 to-transparent" />
          
          {/* 内容区域 */}
          <div className="p-8">
            {/* 标题 */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.5 }}
              className="text-center mb-8"
            >
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400 bg-clip-text text-transparent mb-2">
                创建账号
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                填写信息开始使用 Geo-Agent
              </p>
            </motion.div>

            {/* 表单 */}
          <form onSubmit={handleRegister} className="space-y-4">
            {/* 用户名 */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3, duration: 0.5 }}
            >
              <label htmlFor="username" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                用户名
              </label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <User className={`h-5 w-5 transition-colors duration-200 ${
                    focusedField === 'username' ? 'text-blue-500' : 'text-slate-400 dark:text-slate-500'
                  }`} />
                </div>
                <input
                  id="username"
                  name="username"
                  type="text"
                  value={formData.username}
                  onChange={handleChange}
                  onFocus={() => setFocusedField('username')}
                  onBlur={() => handleBlur('username')}
                  placeholder="设置用户名（至少3个字符）"
                  required
                  className={`w-full pl-10 pr-10 py-3 bg-white/50 dark:bg-[#162031] border-2 rounded-xl text-slate-900 dark:text-slate-100 placeholder-slate-400 transition-all duration-200 focus:outline-none focus:bg-white dark:focus:bg-[#1a2538] ${
                    touched.username && !validation.username
                      ? 'border-red-300 dark:border-red-700 focus:border-red-500'
                      : focusedField === 'username'
                      ? 'border-blue-500 focus:shadow-lg focus:shadow-blue-500/20'
                      : 'border-slate-200 dark:border-white/10 hover:border-slate-300 dark:hover:border-white/15'
                  }`}
                />
                {touched.username && (
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                    {validation.username ? (
                      <Check className="h-5 w-5 text-green-500" />
                    ) : (
                      <X className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                )}
                {focusedField === 'username' && (
                  <motion.div
                    layoutId="inputGlow"
                    className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500/20 to-indigo-500/20 -z-10 blur-xl"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
              </div>
            </motion.div>
            
            {/* 邮箱 */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.35, duration: 0.5 }}
            >
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                邮箱
              </label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className={`h-5 w-5 transition-colors duration-200 ${
                    focusedField === 'email' ? 'text-blue-500' : 'text-slate-400 dark:text-slate-500'
                  }`} />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  onFocus={() => setFocusedField('email')}
                  onBlur={() => handleBlur('email')}
                  placeholder="your@email.com"
                  required
                  className={`w-full pl-10 pr-10 py-3 bg-white/50 dark:bg-[#162031] border-2 rounded-xl text-slate-900 dark:text-slate-100 placeholder-slate-400 transition-all duration-200 focus:outline-none focus:bg-white dark:focus:bg-[#1a2538] ${
                    touched.email && !validation.email
                      ? 'border-red-300 dark:border-red-700 focus:border-red-500'
                      : focusedField === 'email'
                      ? 'border-blue-500 focus:shadow-lg focus:shadow-blue-500/20'
                      : 'border-slate-200 dark:border-white/10 hover:border-slate-300 dark:hover:border-white/15'
                  }`}
                />
                {touched.email && (
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                    {validation.email ? (
                      <Check className="h-5 w-5 text-green-500" />
                    ) : (
                      <X className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                )}
                {focusedField === 'email' && (
                  <motion.div
                    layoutId="inputGlow"
                    className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500/20 to-indigo-500/20 -z-10 blur-xl"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
              </div>
            </motion.div>

            {/* 姓名 */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4, duration: 0.5 }}
            >
              <label htmlFor="full_name" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                姓名 <span className="text-slate-400 text-xs">(可选)</span>
              </label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <UserCircle className={`h-5 w-5 transition-colors duration-200 ${
                    focusedField === 'full_name' ? 'text-blue-500' : 'text-slate-400 dark:text-slate-500'
                  }`} />
                </div>
                <input
                  id="full_name"
                  name="full_name"
                  type="text"
                  value={formData.full_name}
                  onChange={handleChange}
                  onFocus={() => setFocusedField('full_name')}
                  onBlur={() => handleBlur('full_name')}
                  placeholder="您的姓名"
                  className={`w-full pl-10 pr-4 py-3 bg-white/50 dark:bg-[#162031] border-2 rounded-xl text-slate-900 dark:text-slate-100 placeholder-slate-400 transition-all duration-200 focus:outline-none focus:bg-white dark:focus:bg-[#1a2538] ${
                    focusedField === 'full_name'
                      ? 'border-blue-500 focus:shadow-lg focus:shadow-blue-500/20'
                      : 'border-slate-200 dark:border-white/10 hover:border-slate-300 dark:hover:border-white/15'
                  }`}
                />
                {focusedField === 'full_name' && (
                  <motion.div
                    layoutId="inputGlow"
                    className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500/20 to-indigo-500/20 -z-10 blur-xl"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
              </div>
            </motion.div>
            
            {/* 密码 - 第三步将添加强度指示器和显示/隐藏功能 */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.45, duration: 0.5 }}
            >
              <label htmlFor="password" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                密码
              </label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className={`h-5 w-5 transition-colors duration-200 ${
                    focusedField === 'password' ? 'text-blue-500' : 'text-slate-400 dark:text-slate-500'
                  }`} />
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  onFocus={() => setFocusedField('password')}
                  onBlur={() => handleBlur('password')}
                  placeholder="设置密码（至少6个字符）"
                  required
                  className={`w-full pl-10 pr-4 py-3 bg-white/50 dark:bg-[#162031] border-2 rounded-xl text-slate-900 dark:text-slate-100 placeholder-slate-400 transition-all duration-200 focus:outline-none focus:bg-white dark:focus:bg-[#1a2538] ${
                    touched.password && !validation.password
                      ? 'border-red-300 dark:border-red-700 focus:border-red-500'
                      : focusedField === 'password'
                      ? 'border-blue-500 focus:shadow-lg focus:shadow-blue-500/20'
                      : 'border-slate-200 dark:border-white/10 hover:border-slate-300 dark:hover:border-white/15'
                  }`}
                />
                {focusedField === 'password' && (
                  <motion.div
                    layoutId="inputGlow"
                    className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500/20 to-indigo-500/20 -z-10 blur-xl"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
              </div>
            </motion.div>

            {/* 确认密码 */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5, duration: 0.5 }}
            >
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                确认密码
              </label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className={`h-5 w-5 transition-colors duration-200 ${
                    focusedField === 'confirmPassword' ? 'text-blue-500' : 'text-slate-400 dark:text-slate-500'
                  }`} />
                </div>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  onFocus={() => setFocusedField('confirmPassword')}
                  onBlur={() => handleBlur('confirmPassword')}
                  placeholder="再次输入密码"
                  required
                  className={`w-full pl-10 pr-10 py-3 bg-white/50 dark:bg-[#162031] border-2 rounded-xl text-slate-900 dark:text-slate-100 placeholder-slate-400 transition-all duration-200 focus:outline-none focus:bg-white dark:focus:bg-[#1a2538] ${
                    touched.confirmPassword && !validation.confirmPassword
                      ? 'border-red-300 dark:border-red-700 focus:border-red-500'
                      : focusedField === 'confirmPassword'
                      ? 'border-blue-500 focus:shadow-lg focus:shadow-blue-500/20'
                      : 'border-slate-200 dark:border-white/10 hover:border-slate-300 dark:hover:border-white/15'
                  }`}
                />
                {touched.confirmPassword && (
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                    {validation.confirmPassword ? (
                      <Check className="h-5 w-5 text-green-500" />
                    ) : (
                      <X className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                )}
                {focusedField === 'confirmPassword' && (
                  <motion.div
                    layoutId="inputGlow"
                    className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500/20 to-indigo-500/20 -z-10 blur-xl"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
              </div>
              {/* 密码不匹配提示 */}
              {touched.confirmPassword && !validation.confirmPassword && formData.confirmPassword && (
                <motion.p
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-2 text-sm text-red-600 dark:text-red-400"
                >
                  两次密码不匹配
                </motion.p>
              )}
            </motion.div>
            
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
            
            {/* 注册按钮 */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.5 }}
            >
              <motion.button
                type="submit"
                disabled={loading}
                whileHover={{ scale: loading ? 1 : 1.02 }}
                whileTap={{ scale: loading ? 1 : 0.98 }}
                className="relative w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 dark:from-blue-500 dark:to-indigo-500 dark:hover:from-blue-600 dark:hover:to-indigo-600 text-white font-medium rounded-xl shadow-lg shadow-blue-500/30 hover:shadow-xl hover:shadow-blue-500/40 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 overflow-hidden group"
              >
                {/* 按钮高光效果 */}
                <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000" />
                
                <span className="relative flex items-center justify-center gap-2">
                  {loading && <Loader2 className="h-5 w-5 animate-spin" />}
                  {loading ? '注册中...' : '注册'}
                </span>
              </motion.button>
            </motion.div>
          </form>

          {/* 登录链接 */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.5 }}
            className="mt-6 text-center"
          >
            <p className="text-sm text-slate-600 dark:text-slate-400">
              已有账号？{' '}
              <Link 
                to="/login" 
                className="relative font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors duration-200 group"
              >
                立即登录
                <span className="absolute left-0 bottom-0 w-0 h-0.5 bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400 group-hover:w-full transition-all duration-300" />
              </Link>
            </p>
          </motion.div>
        </div>
      </div>

      {/* 底部阴影 */}
      <div className="absolute -bottom-4 left-4 right-4 h-4 bg-slate-900/5 dark:bg-black/20 rounded-full blur-xl" />
    </motion.div>
  </div>
  )
}
