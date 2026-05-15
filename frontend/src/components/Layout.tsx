import { useEffect, useMemo, useState } from "react"
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom"
import { AnimatePresence, motion } from "framer-motion"
import { useAuthStore } from "../store/useAuthStore"
import { useChatStore } from "../store/useChatStore"
import { useThemeStore } from "../store/useThemeStore"
import { useRouteStore } from "../store/useRouteStore"
import { authService, chatService, type SearchHistoryItem, type UserPreferences } from "../services/api"
import { Button } from "./ui/button"
import { Dialog, DialogContent } from "./ui/dialog"
import {
  CheckCheck,
  CheckSquare,
  Database,
  ExternalLink,
  FileBadge2,
  FileText,
  Globe2,
  History,
  Laptop,
  Loader2,
  Lock,
  MessageCircle,
  MessageSquare,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  RefreshCw,
  Settings2,
  Square,
  Sun,
  Trash2,
  User,
} from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar"
import { ScrollArea } from "./ui/scroll-area"
import { cn } from "@/lib/utils"

type SettingsTab = "general" | "account" | "data" | "terms"
type ThemeOption = "light" | "dark" | "system"
type NoticeTone = "success" | "error"

type NoticeState = {
  tone: NoticeTone
  message: string
} | null

const SETTINGS_TABS: Array<{ id: SettingsTab; label: string; icon: typeof Settings2; description: string }> = [
  { id: "general", label: "通用设置", icon: Settings2, description: "主题、语言与上下文偏好" },
  { id: "account", label: "账号管理", icon: User, description: "资料信息与账户安全" },
  { id: "data", label: "数据管理", icon: Database, description: "搜索历史与知识库维护入口" },
  { id: "terms", label: "服务协议", icon: FileBadge2, description: "服务使用、隐私与责任说明" },
]

const THEME_OPTIONS: Array<{ value: ThemeOption; label: string; icon: typeof Sun }> = [
  { value: "light", label: "浅色", icon: Sun },
  { value: "dark", label: "深色", icon: Moon },
  { value: "system", label: "跟随系统", icon: Laptop },
]

const LANGUAGE_OPTIONS = [
  { value: "zh-CN", label: "简体中文" },
  { value: "en-US", label: "English" },
]

const TERMS_SECTIONS = [
  {
    title: "服务使用说明",
    body:
      "Geo-Agent 面向地质与文献研究工作流，提供智能问答、文献检索、Agent 推理与知识库管理能力。系统设置中的偏好项仅用于改善当前账号的交互体验，不代表对模型输出的真实性、完整性或适用性作出保证。",
  },
  {
    title: "数据与隐私说明",
    body:
      "账号资料、偏好设置、搜索历史与会话数据会与当前登录账号关联保存，用于恢复个人工作区状态。系统不会因为你切换主题、语言或上下文参数而改变数据归属；如需删除知识库或文档，请在文献管理页执行相应操作。",
  },
  {
    title: "文献上传与处理声明",
    body:
      "上传的 PDF、Word 等资料会被解析、切分并写入知识库索引，用于后续问答与 Agent 检索。解析结果可能受原文格式、扫描质量、图片内容与模型能力影响，建议在关键引用、结论生成与学术输出前再次核对原文。",
  },
  {
    title: "风险免责与版本信息",
    body:
      "系统生成内容仅作为研究辅助，不应替代人工判断、同行评审或正式结论。若因网络、模型、索引状态或第三方依赖导致回答偏差、延迟或不可用，Geo-Agent 不承诺连续可用性。当前设置页协议内容为前端静态版本，用于说明当前交互范围与责任边界。",
  },
]

const fieldClassName =
  "h-11 w-full rounded-2xl border border-black/8 bg-white px-4 text-[14px] text-foreground outline-none transition-colors placeholder:text-muted-foreground/80 focus:border-slate-300 dark:border-white/10 dark:bg-[#162031] dark:text-slate-100 dark:focus:border-slate-500"

const selectClassName =
  "h-11 rounded-2xl border border-black/8 bg-white px-4 text-[14px] text-foreground outline-none transition-colors focus:border-slate-300 dark:border-white/10 dark:bg-[#162031] dark:text-slate-100 dark:focus:border-slate-500"

const sectionClassName = "border-b border-black/5 pb-7 last:border-b-0 dark:border-white/8"
const rowClassName = "surface-subtle flex items-center justify-between gap-5 rounded-[24px] px-5 py-4"
const metricClassName = "surface-subtle rounded-[24px] px-5 py-4"

function getErrorMessage(error: unknown, fallback: string) {
  if (typeof error === "object" && error && "response" in error) {
    const response = (error as any).response
    const detail = response?.data?.detail
    if (typeof detail === "string" && detail.trim()) {
      return detail
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message
  }

  return fallback
}

function formatDate(value?: string) {
  if (!value) return ""
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}

function isThemeOption(value: string): value is ThemeOption {
  return value === "light" || value === "dark" || value === "system"
}

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, setUser } = useAuthStore()
  const {
    conversations,
    loadConversations,
    deleteConversation,
    batchDeleteConversations,
    setCurrentConversationId,
    currentConversationId,
    selectedConversationIds,
    isSelectionMode,
    toggleConversationSelection,
    selectAllConversations,
    clearSelection,
    setSelectionMode,
  } = useChatStore()
  const { theme, resolvedTheme, setTheme } = useThemeStore()
  const { setLastRoute } = useRouteStore()

  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [settingsTab, setSettingsTab] = useState<SettingsTab>("general")
  const [settingsLoading, setSettingsLoading] = useState(false)
  const [settingsError, setSettingsError] = useState("")

  const [preferences, setPreferences] = useState<UserPreferences | null>(null)
  const [preferencesForm, setPreferencesForm] = useState({
    theme: theme as ThemeOption,
    language: "zh-CN",
    max_context_messages: 10,
    enable_memory: true,
    default_model: "",
  })
  const [profileForm, setProfileForm] = useState({
    full_name: "",
    avatar_url: "",
  })
  const [passwordForm, setPasswordForm] = useState({
    old_password: "",
    new_password: "",
    confirm_password: "",
  })
  const [searchHistory, setSearchHistory] = useState<SearchHistoryItem[]>([])
  const [collections, setCollections] = useState<Array<{ name: string; count: number; error?: string }>>([])

  const [generalSaving, setGeneralSaving] = useState(false)
  const [profileSaving, setProfileSaving] = useState(false)
  const [passwordSaving, setPasswordSaving] = useState(false)
  const [historyClearing, setHistoryClearing] = useState(false)
  const [rebuildLoading, setRebuildLoading] = useState(false)

  const [generalNotice, setGeneralNotice] = useState<NoticeState>(null)
  const [accountNotice, setAccountNotice] = useState<NoticeState>(null)
  const [dataNotice, setDataNotice] = useState<NoticeState>(null)

  const routeBase = "/" + location.pathname.split("/")[1]

  const totalIndexedChunks = useMemo(
    () => collections.reduce((sum, collection) => sum + (collection.count || 0), 0),
    [collections]
  )

  const generalDirty =
    !!preferences &&
    (preferencesForm.theme !== preferences.theme ||
      preferencesForm.language !== preferences.language ||
      preferencesForm.max_context_messages !== preferences.max_context_messages ||
      preferencesForm.enable_memory !== preferences.enable_memory)

  const profileDirty =
    (profileForm.full_name || "") !== (user?.full_name || "") ||
    (profileForm.avatar_url || "") !== (user?.avatar_url || "")

  const handleNewChat = () => {
    setCurrentConversationId(null)
    navigate("/chat")
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        handleNewChat()
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [navigate, setCurrentConversationId])

  useEffect(() => {
    if (user) {
      loadConversations()
    }
  }, [user, loadConversations])

  useEffect(() => {
    if (location.pathname !== "/login" && location.pathname !== "/register") {
      setLastRoute(location.pathname)
    }
  }, [location.pathname, setLastRoute])

  useEffect(() => {
    if (!isSettingsOpen) return

    let cancelled = false

    const loadSettingsData = async () => {
      setSettingsLoading(true)
      setSettingsError("")
      setGeneralNotice(null)
      setAccountNotice(null)
      setDataNotice(null)

      try {
        const [freshUser, preferenceData, historyData, collectionData] = await Promise.all([
          authService.getCurrentUser(),
          authService.getPreferences(),
          authService.getSearchHistory(12),
          chatService.getCollections(),
        ])

        if (cancelled) return

        setUser(freshUser)
        setProfileForm({
          full_name: freshUser.full_name || "",
          avatar_url: freshUser.avatar_url || "",
        })

        setPreferences(preferenceData)
        setPreferencesForm({
          theme: isThemeOption(preferenceData.theme) ? preferenceData.theme : "system",
          language: preferenceData.language || "zh-CN",
          max_context_messages: preferenceData.max_context_messages || 10,
          enable_memory: preferenceData.enable_memory ?? true,
          default_model: preferenceData.default_model || "",
        })

        if (isThemeOption(preferenceData.theme)) {
          setTheme(preferenceData.theme)
        }

        setSearchHistory(historyData.history || [])
        setCollections(collectionData.collections || [])
        setPasswordForm({ old_password: "", new_password: "", confirm_password: "" })
      } catch (error) {
        if (!cancelled) {
          setSettingsError(getErrorMessage(error, "系统设置加载失败，请稍后重试"))
        }
      } finally {
        if (!cancelled) {
          setSettingsLoading(false)
        }
      }
    }

    loadSettingsData()

    return () => {
      cancelled = true
    }
  }, [isSettingsOpen, setTheme, setUser])

  const getConversationTitle = (title?: string | null) => {
    if (!title?.trim()) return "新对话"
    return title.trim().length > 26 ? `${title.trim().slice(0, 26)}...` : title.trim()
  }

  const handleDeleteChat = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    e.preventDefault()
    if (window.confirm("确定要删除这个会话吗？")) {
      await deleteConversation(id)
      if (currentConversationId === id) {
        handleNewChat()
      }
    }
  }

  const handleConversationClick = (id: number) => {
    if (isSelectionMode) {
      toggleConversationSelection(id)
      return
    }
    setCurrentConversationId(id)
    navigate(`/chat/${id}`)
  }

  const handleBatchDelete = async () => {
    if (selectedConversationIds.size === 0) return
    if (window.confirm(`确定要删除选中的 ${selectedConversationIds.size} 个会话吗？`)) {
      await batchDeleteConversations(Array.from(selectedConversationIds))
      if (currentConversationId && selectedConversationIds.has(currentConversationId)) {
        handleNewChat()
      }
    }
  }

  const handleToggleSelectionMode = () => {
    if (isSelectionMode) {
      clearSelection()
      return
    }
    setSelectionMode(true)
  }

  const handleSelectAll = () => {
    if (selectedConversationIds.size === conversations.length) {
      clearSelection()
      return
    }
    selectAllConversations()
  }

  const handleSavePreferences = async () => {
    setGeneralNotice(null)
    setGeneralSaving(true)

    try {
      const payload = {
        theme: preferencesForm.theme,
        language: preferencesForm.language,
        max_context_messages: Math.max(1, Math.min(50, preferencesForm.max_context_messages)),
        enable_memory: preferencesForm.enable_memory,
      }

      const nextPreferences = await authService.updatePreferences(payload)
      setPreferences(nextPreferences)
      setPreferencesForm((prev) => ({
        ...prev,
        max_context_messages: nextPreferences.max_context_messages,
        theme: isThemeOption(nextPreferences.theme) ? nextPreferences.theme : prev.theme,
        language: nextPreferences.language || prev.language,
        enable_memory: nextPreferences.enable_memory,
        default_model: nextPreferences.default_model || "",
      }))

      if (isThemeOption(nextPreferences.theme)) {
        setTheme(nextPreferences.theme)
      }

      setGeneralNotice({ tone: "success", message: "通用设置已保存" })
    } catch (error) {
      setGeneralNotice({ tone: "error", message: getErrorMessage(error, "通用设置保存失败") })
    } finally {
      setGeneralSaving(false)
    }
  }

  const handleSaveProfile = async () => {
    setAccountNotice(null)
    setProfileSaving(true)

    try {
      const nextUser = await authService.updateCurrentUser({
        full_name: profileForm.full_name.trim(),
        avatar_url: profileForm.avatar_url.trim(),
      })
      setUser(nextUser)
      setProfileForm({
        full_name: nextUser.full_name || "",
        avatar_url: nextUser.avatar_url || "",
      })
      setAccountNotice({ tone: "success", message: "账号资料已更新" })
    } catch (error) {
      setAccountNotice({ tone: "error", message: getErrorMessage(error, "账号资料更新失败") })
    } finally {
      setProfileSaving(false)
    }
  }

  const handleChangePassword = async () => {
    setAccountNotice(null)

    if (!passwordForm.old_password || !passwordForm.new_password || !passwordForm.confirm_password) {
      setAccountNotice({ tone: "error", message: "请完整填写密码信息" })
      return
    }

    if (passwordForm.new_password.length < 6) {
      setAccountNotice({ tone: "error", message: "新密码至少需要 6 位" })
      return
    }

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setAccountNotice({ tone: "error", message: "两次输入的新密码不一致" })
      return
    }

    setPasswordSaving(true)

    try {
      await authService.changePassword({
        old_password: passwordForm.old_password,
        new_password: passwordForm.new_password,
      })
      setPasswordForm({ old_password: "", new_password: "", confirm_password: "" })
      setAccountNotice({ tone: "success", message: "密码修改成功" })
    } catch (error) {
      setAccountNotice({ tone: "error", message: getErrorMessage(error, "密码修改失败") })
    } finally {
      setPasswordSaving(false)
    }
  }

  const handleClearSearchHistory = async () => {
    if (searchHistory.length === 0) return
    if (!window.confirm("确定要清空当前账号的搜索历史吗？")) return

    setDataNotice(null)
    setHistoryClearing(true)

    try {
      await authService.clearSearchHistory()
      setSearchHistory([])
      setDataNotice({ tone: "success", message: "搜索历史已清空" })
    } catch (error) {
      setDataNotice({ tone: "error", message: getErrorMessage(error, "搜索历史清空失败") })
    } finally {
      setHistoryClearing(false)
    }
  }

  const handleRebuildIndex = async () => {
    setDataNotice(null)
    setRebuildLoading(true)

    try {
      await chatService.rebuildIndex()
      const collectionData = await chatService.getCollections()
      setCollections(collectionData.collections || [])
      setDataNotice({ tone: "success", message: "知识库索引已触发重建" })
    } catch (error) {
      setDataNotice({ tone: "error", message: getErrorMessage(error, "索引重建失败") })
    } finally {
      setRebuildLoading(false)
    }
  }

  const renderNotice = (notice: NoticeState) => {
    if (!notice) return null

    return (
      <div
        className={cn(
          "rounded-2xl border px-4 py-3 text-sm",
          notice.tone === "success"
            ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300"
            : "border-red-200 bg-red-50 text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300"
        )}
      >
        {notice.message}
      </div>
    )
  }

  const renderSettingsContent = () => {
    if (settingsLoading) {
      return (
        <div className="flex h-full min-h-[420px] items-center justify-center">
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>正在加载系统设置...</span>
          </div>
        </div>
      )
    }

    if (settingsError) {
      return (
        <div className="flex h-full min-h-[420px] items-center justify-center">
          <div className="max-w-[420px] rounded-3xl border border-red-200 bg-red-50 px-6 py-5 text-center text-sm text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
            {settingsError}
          </div>
        </div>
      )
    }

    if (settingsTab === "general") {
      return (
        <div className="space-y-7">
          {renderNotice(generalNotice)}

          <section className={sectionClassName}>
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h3 className="text-[18px] font-semibold text-foreground">主题与外观</h3>
                <p className="mt-1 text-sm text-muted-foreground">主题会同时写入当前账号偏好，并即时作用于当前工作区。</p>
              </div>
              <div className="text-xs text-muted-foreground">
                当前状态：{theme === "system" ? `跟随系统（${resolvedTheme === "dark" ? "深色" : "浅色"}）` : theme === "dark" ? "深色" : "浅色"}
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              {THEME_OPTIONS.map((option) => {
                const Icon = option.icon
                const active = preferencesForm.theme === option.value
                return (
                  <button
                    key={option.value}
                    onClick={() => {
                      setGeneralNotice(null)
                      setPreferencesForm((prev) => ({ ...prev, theme: option.value }))
                      setTheme(option.value)
                    }}
                    className={cn(
                      "flex h-[104px] flex-col items-center justify-center gap-2.5 rounded-[24px] border text-center transition-colors",
                      active
                        ? "border-slate-300 bg-[#f7f9fc] text-foreground dark:border-white/10 dark:bg-[#22314a] dark:text-slate-100"
                        : "border-black/8 bg-white hover:bg-[#fafbfd] dark:border-white/10 dark:bg-[#162031] dark:text-slate-100 dark:hover:bg-[#1d2940]"
                    )}
                  >
                    <div
                      className={cn(
                        "flex h-11 w-14 items-center justify-center rounded-[16px] border border-black/5 bg-white/90 text-muted-foreground dark:border-white/10",
                        active ? "dark:bg-[#101827] dark:text-slate-100" : "dark:bg-[#0f1726] dark:text-slate-300"
                      )}
                    >
                      <Icon className="h-5 w-5" />
                    </div>
                    <span className="text-[15px] font-medium">{option.label}</span>
                  </button>
                )
              })}
            </div>
          </section>

          <section className={sectionClassName}>
            <div className="mb-5">
              <h3 className="text-[18px] font-semibold text-foreground">偏好设置</h3>
              <p className="mt-1 text-sm text-muted-foreground">控制语言、上下文记忆与当前工作区的默认行为。</p>
            </div>
            <div className="space-y-3">
              <div className={rowClassName}>
                <div className="min-w-0 flex-1">
                  <div className="text-[14px] font-medium text-foreground">界面语言</div>
                  <div className="mt-1 text-xs text-muted-foreground">当前只提供基础语言切换入口。</div>
                </div>
                <select
                  value={preferencesForm.language}
                  onChange={(e) => {
                    setGeneralNotice(null)
                    setPreferencesForm((prev) => ({ ...prev, language: e.target.value }))
                  }}
                  className={cn(selectClassName, "w-[176px] shrink-0")}
                >
                  {LANGUAGE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className={rowClassName}>
                <div className="min-w-0 flex-1">
                  <div className="text-[14px] font-medium text-foreground">上下文消息数</div>
                  <div className="mt-1 text-xs text-muted-foreground">控制对话中保留的上下文消息窗口大小，范围 1-50。</div>
                </div>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={preferencesForm.max_context_messages}
                  onChange={(e) => {
                    setGeneralNotice(null)
                    const next = Number(e.target.value)
                    setPreferencesForm((prev) => ({
                      ...prev,
                      max_context_messages: Number.isFinite(next) ? next : prev.max_context_messages,
                    }))
                  }}
                  className={cn(fieldClassName, "w-[104px] shrink-0 text-center")}
                />
              </div>

              <div className={rowClassName}>
                <div className="min-w-0 flex-1">
                  <div className="text-[14px] font-medium text-foreground">启用记忆</div>
                  <div className="mt-1 text-xs text-muted-foreground">决定系统是否保留更稳定的个人上下文偏好。</div>
                </div>
                <button
                  onClick={() => {
                    setGeneralNotice(null)
                    setPreferencesForm((prev) => ({ ...prev, enable_memory: !prev.enable_memory }))
                  }}
                  className={cn(
                    "inline-flex h-11 shrink-0 items-center rounded-full px-4 text-sm font-medium transition-colors",
                    preferencesForm.enable_memory
                      ? "bg-slate-900 text-white dark:bg-[#355ea8] dark:text-white"
                      : "bg-white text-muted-foreground ring-1 ring-black/8 hover:text-foreground dark:bg-[#162031] dark:text-slate-300 dark:ring-white/10"
                  )}
                >
                  {preferencesForm.enable_memory ? "已启用" : "已关闭"}
                </button>
              </div>

              <div className={rowClassName}>
                <div className="min-w-0 flex-1">
                  <div className="text-[14px] font-medium text-foreground">默认模型</div>
                  <div className="mt-1 text-xs text-muted-foreground">当前仓库未提供稳定的模型候选源，这里只展示已保存值。</div>
                </div>
                <div className="shrink-0 text-sm text-muted-foreground">{preferencesForm.default_model || "未设置"}</div>
              </div>
            </div>
          </section>

          <div className="flex justify-end">
            <Button
              onClick={handleSavePreferences}
              disabled={!generalDirty || generalSaving}
              className="h-11 rounded-full px-5 text-sm"
            >
              {generalSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              保存通用设置
            </Button>
          </div>
        </div>
      )
    }

    if (settingsTab === "account") {
      return (
        <div className="space-y-7">
          {renderNotice(accountNotice)}

          <section className={sectionClassName}>
            <div className="mb-5">
              <h3 className="text-[18px] font-semibold text-foreground">基本资料</h3>
              <p className="mt-1 text-sm text-muted-foreground">用户名与邮箱为只读项，昵称和头像地址会同步更新侧栏展示。</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">用户名</label>
                <input value={user?.username || ""} readOnly className={cn(fieldClassName, "bg-[#f7f9fc] text-muted-foreground dark:bg-[#0d1528]")} />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">邮箱</label>
                <input value={user?.email || ""} readOnly className={cn(fieldClassName, "bg-[#f7f9fc] text-muted-foreground dark:bg-[#0d1528]")} />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">昵称 / 全名</label>
                <input
                  value={profileForm.full_name}
                  onChange={(e) => {
                    setAccountNotice(null)
                    setProfileForm((prev) => ({ ...prev, full_name: e.target.value }))
                  }}
                  placeholder="输入展示名称"
                  className={fieldClassName}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">头像 URL</label>
                <input
                  value={profileForm.avatar_url}
                  onChange={(e) => {
                    setAccountNotice(null)
                    setProfileForm((prev) => ({ ...prev, avatar_url: e.target.value }))
                  }}
                  placeholder="https://"
                  className={fieldClassName}
                />
              </div>
            </div>
            <div className="mt-5 flex justify-end">
              <Button onClick={handleSaveProfile} disabled={!profileDirty || profileSaving} className="h-11 rounded-full px-5 text-sm">
                {profileSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                保存资料
              </Button>
            </div>
          </section>

          <section className={sectionClassName}>
            <div className="mb-5 flex items-start gap-3">
              <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-2xl bg-[#f7f9fc] text-muted-foreground dark:bg-[#0d1528]">
                <Lock className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-[18px] font-semibold text-foreground">安全设置</h3>
                <p className="mt-1 text-sm text-muted-foreground">修改密码前会先校验原密码，前端会拦截明显无效的输入。</p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">原密码</label>
                <input
                  type="password"
                  value={passwordForm.old_password}
                  onChange={(e) => {
                    setAccountNotice(null)
                    setPasswordForm((prev) => ({ ...prev, old_password: e.target.value }))
                  }}
                  className={fieldClassName}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">新密码</label>
                <input
                  type="password"
                  value={passwordForm.new_password}
                  onChange={(e) => {
                    setAccountNotice(null)
                    setPasswordForm((prev) => ({ ...prev, new_password: e.target.value }))
                  }}
                  className={fieldClassName}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">确认新密码</label>
                <input
                  type="password"
                  value={passwordForm.confirm_password}
                  onChange={(e) => {
                    setAccountNotice(null)
                    setPasswordForm((prev) => ({ ...prev, confirm_password: e.target.value }))
                  }}
                  className={fieldClassName}
                />
              </div>
            </div>
            <div className="mt-5 flex justify-end">
              <Button onClick={handleChangePassword} disabled={passwordSaving} className="h-11 rounded-full px-5 text-sm">
                {passwordSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                修改密码
              </Button>
            </div>
          </section>
        </div>
      )
    }

    if (settingsTab === "data") {
      return (
        <div className="space-y-7">
          {renderNotice(dataNotice)}

          <section className={sectionClassName}>
            <div className="mb-5">
              <h3 className="text-[18px] font-semibold text-foreground">知识库概览</h3>
              <p className="mt-1 text-sm text-muted-foreground">这里保留高频维护入口，复杂的文献治理仍回到文献管理页处理。</p>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className={metricClassName}>
                <div className="text-xs text-muted-foreground">知识库集合数</div>
                <div className="mt-2 text-[24px] font-semibold text-foreground">{collections.length}</div>
              </div>
              <div className={metricClassName}>
                <div className="text-xs text-muted-foreground">向量片段总数</div>
                <div className="mt-2 text-[24px] font-semibold text-foreground">{totalIndexedChunks}</div>
              </div>
              <div className={metricClassName}>
                <div className="text-xs text-muted-foreground">当前搜索历史</div>
                <div className="mt-2 text-[24px] font-semibold text-foreground">{searchHistory.length}</div>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap gap-3">
              <Button
                variant="outline"
                className="h-11 rounded-full border-black/8 bg-white px-5 text-sm hover:bg-slate-50 dark:border-white/10 dark:bg-[#162031] dark:hover:bg-[#1d2940]"
                onClick={() => {
                  setIsSettingsOpen(false)
                  navigate("/documents")
                }}
              >
                <ExternalLink className="mr-2 h-4 w-4" />
                前往文献管理
              </Button>
              <Button onClick={handleRebuildIndex} disabled={rebuildLoading} className="h-11 rounded-full px-5 text-sm">
                {rebuildLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                重建索引
              </Button>
            </div>

            <div className="mt-6 space-y-2">
              {collections.slice(0, 6).map((collection) => (
                <div key={collection.name} className={cn(rowClassName, "py-3")}>
                  <div className="min-w-0">
                    <div className="truncate text-[14px] font-medium text-foreground">{collection.name}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{collection.error ? "索引状态异常" : "可在文献管理页继续维护"}</div>
                  </div>
                  <div className="shrink-0 text-sm text-muted-foreground">{collection.count} 条</div>
                </div>
              ))}
              {collections.length === 0 && (
                <div className="rounded-[24px] bg-[#f7f9fc] px-5 py-5 text-sm text-muted-foreground dark:bg-[#0d1528]">
                  当前没有可展示的知识库集合。
                </div>
              )}
            </div>
          </section>

          <section className={sectionClassName}>
            <div className="mb-5 flex items-start gap-3">
              <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-2xl bg-[#f7f9fc] text-muted-foreground dark:bg-[#0d1528]">
                <History className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-[18px] font-semibold text-foreground">搜索历史</h3>
                <p className="mt-1 text-sm text-muted-foreground">仅展示当前账号最近的检索记录，支持一键清空。</p>
              </div>
            </div>

            <div className="space-y-2">
              {searchHistory.map((item) => (
                <div key={item.id} className={cn(rowClassName, "py-4")}>
                  <div className="min-w-0">
                    <div className="truncate text-[14px] font-medium text-foreground">{item.query}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {item.search_type.toUpperCase()} · {item.result_count ?? 0} 条结果 · {formatDate(item.created_at)}
                    </div>
                  </div>
                  <div className="shrink-0 text-xs text-muted-foreground">
                    {item.response_time ? `${item.response_time} ms` : "未记录耗时"}
                  </div>
                </div>
              ))}
              {searchHistory.length === 0 && (
                <div className="rounded-[24px] bg-[#f7f9fc] px-5 py-5 text-sm text-muted-foreground dark:bg-[#0d1528]">
                  当前没有搜索历史记录。
                </div>
              )}
            </div>

            <div className="mt-5 flex justify-end">
              <Button
                variant="outline"
                onClick={handleClearSearchHistory}
                disabled={historyClearing || searchHistory.length === 0}
                className="h-11 rounded-full border-black/8 bg-white px-5 text-sm hover:bg-slate-50 dark:border-white/10 dark:bg-[#162031] dark:hover:bg-[#1d2940]"
              >
                {historyClearing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
                清空搜索历史
              </Button>
            </div>
          </section>
        </div>
      )
    }

    return (
      <div className="space-y-6">
        <div className="rounded-[24px] bg-[#f7f9fc] px-5 py-4 text-sm leading-7 text-slate-600 dark:bg-[#0d1528] dark:text-slate-300">
          本页协议内容用于说明当前 Geo-Agent 系统设置、知识库处理和账号数据的使用边界。若后续仓库引入正式的可配置协议源，应以服务端发布版本为准。
        </div>

        {TERMS_SECTIONS.map((section) => (
          <section key={section.title} className={sectionClassName}>
            <h3 className="text-[18px] font-semibold text-foreground">{section.title}</h3>
            <p className="mt-3 text-[14px] leading-7 text-slate-600 dark:text-slate-300">{section.body}</p>
          </section>
        ))}
      </div>
    )
  }

  const currentTab = SETTINGS_TABS.find((tab) => tab.id === settingsTab) ?? SETTINGS_TABS[0]

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      <aside
        className={cn(
          "app-shell flex h-full shrink-0 flex-col transition-all duration-300",
          isSidebarOpen ? "w-[248px]" : "w-[72px]"
        )}
      >
        <div className="relative flex items-center justify-between px-4 pb-5 pt-6">
          <div className={cn("flex min-w-0 items-center gap-2.5", !isSidebarOpen && "justify-center")}>
            <div className="flex h-8 w-8 items-center justify-center rounded-2xl bg-transparent text-primary">
              <Globe2 className="h-4 w-4" aria-hidden="true" />
            </div>
            {isSidebarOpen && (
              <div className="min-w-0">
                <p className="truncate text-[18px] font-semibold tracking-[-0.01em] text-[#3b67f6]">deepseek</p>
              </div>
            )}
          </div>

          <button
            onClick={() => setIsSidebarOpen((prev) => !prev)}
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-black/5 hover:text-foreground dark:hover:bg-white/5",
              !isSidebarOpen && "mx-auto"
            )}
            title={isSidebarOpen ? "收起侧边栏" : "展开侧边栏"}
          >
            {isSidebarOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
          </button>
        </div>

        <div className="px-3 pb-5">
          <button
            onClick={handleNewChat}
            className={cn(
              "flex w-full items-center rounded-[22px] border border-black/6 bg-white text-left text-foreground shadow-[0_1px_3px_rgba(15,23,42,0.06),0_8px_18px_rgba(15,23,42,0.03)] transition-all duration-200 hover:bg-slate-50 dark:border-white/8 dark:bg-[#202938] dark:text-slate-100 dark:shadow-none dark:hover:bg-[#253041]",
              isSidebarOpen ? "gap-3 px-4 py-[13px]" : "justify-center px-0 py-3"
            )}
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-50 text-foreground dark:bg-[#313b4d] dark:text-slate-100">
              <Plus className="h-3.5 w-3.5" />
            </div>
            {isSidebarOpen && (
              <div className="min-w-0">
                <div className="text-[15px] font-semibold">开启新对话</div>
              </div>
            )}
          </button>
        </div>

        <nav className="px-3 pb-2">
          <div className="flex flex-col gap-1">
            <Link
              to="/chat"
              className={cn(
                "nav-pill flex items-center justify-center gap-3",
                location.pathname.startsWith("/chat") && "nav-pill-active",
                !isSidebarOpen && "justify-center"
              )}
            >
              <MessageSquare className="h-4 w-4 shrink-0" />
              {isSidebarOpen && <span>智能问答</span>}
            </Link>
            <Link
              to="/documents"
              className={cn(
                "nav-pill flex items-center justify-center gap-3",
                location.pathname.startsWith("/documents") && "nav-pill-active",
                !isSidebarOpen && "justify-center"
              )}
            >
              <FileText className="h-4 w-4 shrink-0" />
              {isSidebarOpen && <span>文献管理</span>}
            </Link>
          </div>
        </nav>

        <div className="flex min-h-0 flex-1 flex-col">
          {isSidebarOpen && conversations.length > 0 && (
            <div className="flex items-center justify-between px-4 pb-2 pt-3">
              <div>
                <div className="text-sm font-medium text-muted-foreground">最近会话</div>
              </div>
              {conversations.length > 0 && (
                <div className="flex items-center gap-1">
                  {isSelectionMode && (
                    <>
                      <button
                        onClick={handleSelectAll}
                        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                        title={selectedConversationIds.size === conversations.length ? "取消全选" : "全选"}
                      >
                        {selectedConversationIds.size === conversations.length ? (
                          <CheckCheck className="h-4 w-4 text-primary" />
                        ) : (
                          <CheckSquare className="h-4 w-4" />
                        )}
                      </button>
                      <button
                        onClick={handleBatchDelete}
                        disabled={selectedConversationIds.size === 0}
                        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive disabled:opacity-40"
                        title={`删除选中 (${selectedConversationIds.size})`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </>
                  )}
                  <button
                    onClick={handleToggleSelectionMode}
                    className={cn(
                      "rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors",
                      isSelectionMode
                        ? "border-primary/20 bg-primary/12 text-primary dark:border-primary/25 dark:bg-primary/15"
                        : "border-black/6 bg-slate-100 text-muted-foreground hover:text-foreground dark:border-white/8 dark:bg-[#202938] dark:text-slate-400 dark:hover:bg-[#253041] dark:hover:text-slate-100"
                    )}
                  >
                    {isSelectionMode ? "取消" : "管理"}
                  </button>
                </div>
              )}
            </div>
          )}

          <ScrollArea className="min-h-0 flex-1 px-3 pb-3">
            {isSidebarOpen && conversations.length === 0 ? (
              <div className="flex h-full min-h-[320px] flex-col items-center justify-center px-5 text-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full border border-black/6 bg-white/70 text-muted-foreground dark:border-white/8 dark:bg-white/5 dark:text-slate-400">
                  <History className="h-4 w-4" />
                </div>
                <p className="mt-4 text-[13px] font-medium text-muted-foreground">暂无历史对话</p>
              </div>
            ) : (
            <div className="space-y-0.5">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  onClick={() => handleConversationClick(conv.id)}
                  className={cn(
                    "group cursor-pointer rounded-2xl px-3 py-2 transition-colors",
                    isSidebarOpen ? "flex items-start gap-2.5" : "flex justify-center px-0",
                    currentConversationId === conv.id && !isSelectionMode
                      ? "bg-white text-foreground shadow-sm dark:bg-[#1b2638] dark:text-slate-100 dark:shadow-none"
                      : "text-foreground/85 hover:bg-white/70 dark:text-slate-300 dark:hover:bg-white/5",
                    isSelectionMode && selectedConversationIds.has(conv.id) && "bg-white text-foreground shadow-sm dark:bg-[#1b2638] dark:text-slate-100 dark:shadow-none"
                  )}
                  title={conv.title || "新对话"}
                >
                  {isSelectionMode ? (
                    selectedConversationIds.has(conv.id) ? (
                      <CheckSquare className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                    ) : (
                      <Square className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    )
                  ) : (
                    <MessageCircle className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                  )}

                  {isSidebarOpen && (
                    <>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[12.5px] font-medium">{getConversationTitle(conv.title)}</p>
                      </div>
                      {!isSelectionMode && (
                        <button
                          type="button"
                          onClick={(e) => handleDeleteChat(e, conv.id)}
                          className="opacity-0 transition-opacity group-hover:opacity-100"
                          title="删除会话"
                        >
                          <span className="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive">
                            <Trash2 className="h-4 w-4" />
                          </span>
                        </button>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
            )}
          </ScrollArea>
        </div>

        <div className="border-t border-black/5 px-3 py-4">
          <div className={cn("rounded-[20px] bg-transparent px-3 py-2", !isSidebarOpen && "px-0")}>
            <div className={cn("flex items-center gap-3", !isSidebarOpen && "justify-center")}>
              <Avatar className="h-9 w-9">
                <AvatarImage src={user?.avatar_url} />
                <AvatarFallback>{user?.username?.[0]?.toUpperCase()}</AvatarFallback>
              </Avatar>

              {isSidebarOpen && (
                <>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">{user?.full_name || user?.username}</p>
                    <p className="truncate text-[11px] text-muted-foreground">已登录</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-9 w-9 rounded-xl border border-black/5 bg-white/80 text-muted-foreground hover:bg-black/5 dark:border-white/8 dark:bg-[#162031] dark:hover:bg-[#1d2940]"
                    onClick={() => setIsSettingsOpen(true)}
                    title="系统设置"
                  >
                    <Settings2 className="h-4 w-4" />
                  </Button>
                </>
              )}
            </div>
          </div>

          {!isSidebarOpen && (
            <div className="mt-3 flex flex-col items-center gap-1.5">
              <Button
                variant="ghost"
                size="icon"
                className="h-9 w-9 rounded-xl border border-black/5 bg-white/80 text-muted-foreground hover:bg-black/5 dark:border-white/8 dark:bg-[#162031] dark:hover:bg-[#1d2940]"
                onClick={() => setIsSettingsOpen(true)}
                title="系统设置"
              >
                <Settings2 className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </aside>

      <main className="relative min-w-0 flex-1 overflow-hidden bg-white dark:bg-[#0d1320]">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={routeBase}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.18, ease: [0.2, 0.8, 0.2, 1] }}
            className="relative h-full"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>

      <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
        <DialogContent className="h-[min(760px,calc(100dvh-48px))] w-[min(1080px,calc(100vw-48px))] max-w-none gap-0 overflow-hidden rounded-[28px] border border-black/5 bg-white p-0 shadow-[0_24px_80px_rgba(15,23,42,0.18)] dark:border-white/8 dark:bg-[#111827] [&>button]:right-6 [&>button]:top-5">
          <div className="flex h-full min-h-0">
            <div className="flex h-full w-[228px] shrink-0 flex-col border-r border-black/5 bg-[#f7f9fc] px-4 py-5 dark:border-white/8 dark:bg-[#101827]">
              <div className="mb-6 text-[20px] font-semibold tracking-[-0.01em] text-foreground">系统设置</div>
              <div className="space-y-1.5">
                {SETTINGS_TABS.map((tab) => {
                  const Icon = tab.icon
                  const active = settingsTab === tab.id
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setSettingsTab(tab.id)}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left text-[15px] transition-colors",
                        active
                          ? "bg-white text-foreground shadow-sm dark:bg-[#1c2638] dark:text-slate-100"
                          : "text-muted-foreground hover:bg-white/75 hover:text-foreground dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-slate-100"
                      )}
                    >
                      <Icon className="h-5 w-5 shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="truncate font-medium">{tab.label}</div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="flex min-w-0 flex-1 flex-col bg-white dark:bg-[#111827]">
              <div className="shrink-0 border-b border-black/5 px-8 py-6 dark:border-white/8">
                <div className="text-[22px] font-semibold tracking-[-0.01em] text-foreground">{currentTab.label}</div>
                <div className="mt-1.5 text-sm text-muted-foreground">{currentTab.description}</div>
              </div>
              <ScrollArea className="min-h-0 flex-1">
                <div className="mx-auto w-full max-w-[780px] px-8 py-7">{renderSettingsContent()}</div>
              </ScrollArea>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
