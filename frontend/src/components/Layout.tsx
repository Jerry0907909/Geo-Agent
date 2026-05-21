import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom"
import { AnimatePresence, LayoutGroup, motion, useReducedMotion } from "framer-motion"
import {
  BookOpen,
  CheckCheck,
  CheckSquare,
  Eye,
  EyeOff,
  FileText,
  Key,
  Languages,
  Loader2,
  LogOut,
  MessageCircle,
  MessageSquare,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Search,
  Settings2,
  Shield,
  Sparkles,
  Square,
  Sun,
  Trash2,
} from "lucide-react"
import { authService } from "../services/api"
import { useAuthStore } from "../store/useAuthStore"
import { useChatStore } from "../store/useChatStore"
import { useThemeStore } from "../store/useThemeStore"
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar"
import { Button } from "./ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog"
import { Input } from "./ui/input"
import { ScrollArea } from "./ui/scroll-area"
import { cn } from "@/lib/utils"
import { APP_SPRING, GENTLE_SPRING, PAGE_FORWARD, PAGE_BACKWARD, REDUCED_FADE, SOFT_SPRING, TAB_SWITCH } from "@/lib/motion"

type SettingsTab = "general" | "account" | "data" | "policy"
type SourcePreference = "knowledge" | "web" | "auto"
type SummaryStyle = "concise" | "expanded"

const PAGE_META = {
  documents: { title: "知识库管理", description: "维护知识库集合、上传资料和预览内容" },
}

const NAV_ITEMS = [
  { to: "/chat", match: "/chat", label: "智能问答", icon: MessageSquare },
  { to: "/documents", match: "/documents", label: "知识库管理", icon: FileText },
] as const

const SETTINGS_TABS: Array<{ key: SettingsTab; label: string; icon: typeof Sparkles }> = [
  { key: "general", label: "通用设置", icon: Sparkles },
  { key: "account", label: "账号管理", icon: Shield },
  { key: "data", label: "数据管理", icon: BookOpen },
  { key: "policy", label: "服务协议", icon: FileText },
]

const SOURCE_OPTIONS: Array<{ key: SourcePreference; label: string }> = [
  { key: "knowledge", label: "知识库优先" },
  { key: "web", label: "网络优先" },
  { key: "auto", label: "自动选择" },
]

const SUMMARY_OPTIONS: Array<{ key: SummaryStyle; label: string }> = [
  { key: "concise", label: "仅展示摘要" },
  { key: "expanded", label: "展开细节" },
]

function getConversationTitle(title?: string | null) {
  if (!title) return "新对话"
  const text = title.trim()
  if (!text) return "新对话"
  return text.length > 26 ? `${text.slice(0, 26)}...` : text
}

function getConversationGroupLabel(updatedAt: string) {
  const updated = new Date(updatedAt)
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - updated.getTime()) / 86400000)
  if (updated.toDateString() === now.toDateString()) return "今天"
  if (diffDays <= 7) return "近 7 天"
  return "更早"
}

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
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
  const { theme, setTheme, toggleTheme } = useThemeStore()
  const shouldReduceMotion = useReducedMotion()

  // ---------- shell state ----------
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [settingsTab, setSettingsTab] = useState<SettingsTab>("general")
  const [language, setLanguage] = useState("zh-CN")
  const [sourcePreference, setSourcePreference] = useState<SourcePreference>("knowledge")
  const [summaryStyle, setSummaryStyle] = useState<SummaryStyle>("concise")
  const [autoOpenSources, setAutoOpenSources] = useState(true)

  // ---------- password change state ----------
  const [pwOld, setPwOld] = useState("")
  const [pwNew, setPwNew] = useState("")
  const [pwConfirm, setPwConfirm] = useState("")
  const [pwError, setPwError] = useState("")
  const [pwSuccess, setPwSuccess] = useState("")
  const [pwLoading, setPwLoading] = useState(false)
  const [showOldPw, setShowOldPw] = useState(false)
  const [showNewPw, setShowNewPw] = useState(false)
  const [showConfirmPw, setShowConfirmPw] = useState(false)

  const [policyView, setPolicyView] = useState<string | null>(null)

  // ---------- derived ----------
  const routeBase = location.pathname.startsWith("/documents") ? "documents" : "chat"
  const isChatRoute = location.pathname.startsWith("/chat")

  // Navigation direction tracking for page transitions
  const [navDirection, setNavDirection] = useState<"forward" | "backward">("forward")
  const prevRouteBase = useRef(routeBase)
  useEffect(() => {
    if (prevRouteBase.current !== routeBase) {
      // Chat → Documents = forward, Documents → Chat = backward
      setNavDirection(routeBase === "documents" ? "forward" : "backward")
      prevRouteBase.current = routeBase
    }
  }, [routeBase])

  const pageVariants = shouldReduceMotion
    ? REDUCED_FADE
    : navDirection === "forward"
      ? PAGE_FORWARD
      : PAGE_BACKWARD

  const pageMeta = useMemo(() => PAGE_META.documents, [])

  const groupedConversations = useMemo(() => {
    const groups = new Map<string, typeof conversations>()
    conversations.forEach((conversation) => {
      const label = getConversationGroupLabel(conversation.updated_at)
      const current = groups.get(label) ?? []
      current.push(conversation)
      groups.set(label, current)
    })
    return ["今天", "近 7 天", "更早"]
      .map((label) => ({ label, items: groups.get(label) ?? [] }))
      .filter((group) => group.items.length > 0)
  }, [conversations])

  // ---------- effects ----------
  useEffect(() => { if (user) loadConversations() }, [loadConversations, user])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        setCurrentConversationId(null)
        navigate("/chat")
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [navigate, setCurrentConversationId])

  // ---------- handlers ----------
  const handleNewChat = () => { setCurrentConversationId(null); navigate("/chat") }
  const handleLogout = () => { logout(); navigate("/login") }

  const handleDeleteChat = async (event: React.MouseEvent, id: number) => {
    event.stopPropagation(); event.preventDefault()
    if (window.confirm("确定要删除这个会话吗？")) {
      await deleteConversation(id)
      if (currentConversationId === id) handleNewChat()
    }
  }

  const handleConversationClick = (id: number) => {
    if (isSelectionMode) { toggleConversationSelection(id); return }
    setCurrentConversationId(id)
    navigate(`/chat/${id}`)
  }

  const handleBatchDelete = async () => {
    if (selectedConversationIds.size === 0) return
    if (window.confirm(`确定要删除选中的 ${selectedConversationIds.size} 个会话吗？`)) {
      await batchDeleteConversations(Array.from(selectedConversationIds))
      if (currentConversationId && selectedConversationIds.has(currentConversationId)) handleNewChat()
    }
  }

  const openSettings = useCallback((tab: SettingsTab = "general") => {
    setSettingsTab(tab)
    setIsSettingsOpen(true)
    setPwOld(""); setPwNew(""); setPwConfirm("")
    setPwError(""); setPwSuccess("")
  }, [])

  const handlePasswordChange = async () => {
    setPwError(""); setPwSuccess("")
    if (pwNew.length < 6 || pwConfirm.length < 6) { setPwError("新密码至少 6 位"); return }
    if (pwNew !== pwConfirm) { setPwError("两次输入的新密码不一致"); return }
    setPwLoading(true)
    try {
      await authService.changePassword({ old_password: pwOld, new_password: pwNew, confirm_password: pwConfirm })
      setPwSuccess("密码修改成功")
      setPwOld(""); setPwNew(""); setPwConfirm("")
    } catch (err: any) {
      setPwError(err?.response?.data?.detail || "修改失败")
    } finally {
      setPwLoading(false)
    }
  }

  const userDisplayName = user?.full_name || user?.username || "Geo-Agent"
  const userInitial = userDisplayName.slice(0, 1).toUpperCase()

  return (
    <>
      <LayoutGroup id="geo-agent-shell">
        <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
          {/* =========== SIDEBAR =========== */}
          <motion.aside
            layout
            animate={{ width: isSidebarOpen ? 244 : 68 }}
            transition={APP_SPRING}
            className="flex h-full shrink-0 flex-col border-r border-border/70 bg-[#fafbfd] dark:bg-card"
          >
            <button
              type="button"
              onClick={() => navigate("/chat")}
              className={cn("flex items-center gap-3 px-4 pb-3 pt-4 text-left", !isSidebarOpen && "justify-center px-0")}
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-sm font-semibold text-primary">
                G
              </div>
              {isSidebarOpen && (
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">Geo-Agent</p>
                </div>
              )}
            </button>

            <div className="px-3 pb-3">
              <Button
                onClick={handleNewChat}
                className={cn("h-[42px] w-full justify-between rounded-full px-4 text-sm shadow-ds-surface", !isSidebarOpen && "justify-center px-0")}
              >
                <span className="flex items-center gap-2"><Plus className="h-4 w-4" />{isSidebarOpen && <span>开启新对话</span>}</span>
                {isSidebarOpen && <span className="rounded-full bg-white/18 px-2 py-0.5 text-[11px] text-primary-foreground/90">Ctrl K</span>}
              </Button>
            </div>

            <nav className="space-y-1 px-3">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon
                const isActive = location.pathname.startsWith(item.match)
                return (
                  <Button key={item.to} variant="ghost" className={cn("relative h-10 w-full overflow-hidden rounded-2xl px-3", !isSidebarOpen ? "justify-center px-0" : "justify-start")} asChild>
                    <Link to={item.to}>
                      {isActive && (
                        <motion.span layoutId="sidebar-nav-active" transition={SOFT_SPRING} className="absolute inset-0 rounded-2xl border border-[#b7c8fe] bg-primary/10 dark:border-[#3c4f8d] dark:bg-[#1f2942]" />
                      )}
                      <span className={cn("relative flex items-center gap-2", !isSidebarOpen && "justify-center", isActive ? "text-primary" : "text-foreground")}>
                        <Icon className="h-4 w-4 shrink-0" />{isSidebarOpen && <span>{item.label}</span>}
                      </span>
                    </Link>
                  </Button>
                )
              })}
            </nav>

            <div className="mt-4 flex min-h-0 flex-1 flex-col">
              {isSidebarOpen && (
                <div className="flex items-center justify-between px-4 pb-2">
                  <p className="text-xs text-muted-foreground">历史对话</p>
                  {conversations.length > 0 && (
                    <div className="flex items-center gap-1">
                      {isSelectionMode && (<>
                        <Button variant="ghost" size="icon" className="h-7 w-7"
                          onClick={() => selectedConversationIds.size === conversations.length ? (clearSelection(), setSelectionMode(true)) : selectAllConversations()}
                          title={selectedConversationIds.size === conversations.length ? "取消全选" : "全选"}>
                          {selectedConversationIds.size === conversations.length ? <CheckCheck className="h-3.5 w-3.5" /> : <CheckSquare className="h-3.5 w-3.5" />}
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive" disabled={selectedConversationIds.size === 0} onClick={handleBatchDelete} title="删除选中">
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </>)}
                      <Button variant={isSelectionMode ? "secondary" : "ghost"} size="sm" className="h-7 px-2.5"
                        onClick={() => isSelectionMode ? clearSelection() : setSelectionMode(true)}>
                        {isSelectionMode ? "取消" : "管理"}
                      </Button>
                    </div>
                  )}
                </div>
              )}
              <ScrollArea className="min-h-0 flex-1 px-2">
                {groupedConversations.length === 0 ? (
                  <div className={cn("px-2 py-6 text-center text-xs text-muted-foreground", !isSidebarOpen && "px-0")}>{isSidebarOpen ? "还没有历史对话" : "—"}</div>
                ) : (
                  <div className="space-y-4 pb-4">
                    {groupedConversations.map((group) => (
                      <div key={group.label} className="space-y-1">
                        {isSidebarOpen && <p className="px-2 text-[11px] text-muted-foreground">{group.label}</p>}
                        {group.items.map((conversation) => {
                          const isActive = currentConversationId === conversation.id && !isSelectionMode
                          const isSelected = isSelectionMode && selectedConversationIds.has(conversation.id)
                          return (
                            <motion.div key={conversation.id} layout="position" transition={SOFT_SPRING}
                              onClick={() => handleConversationClick(conversation.id)}
                              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleConversationClick(conversation.id) } }}
                              role="button" tabIndex={0}
                              className={cn("group relative flex w-full items-center gap-2 rounded-2xl border border-transparent px-3 py-2 text-left text-sm transition-colors hover:bg-secondary", isSelected && "border-[#b7c8fe] bg-primary/10", !isSidebarOpen && "justify-center px-0")}
                              title={conversation.title || "新对话"}>
                              {isActive && <motion.span layoutId="conversation-active" transition={SOFT_SPRING} className="absolute inset-0 rounded-2xl border border-[#b7c8fe] bg-primary/10 dark:border-[#3c4f8d] dark:bg-[#1f2942]" />}
                              <div className={cn("relative flex w-full items-center gap-2", !isSidebarOpen && "justify-center")}>
                                {isSelectionMode ? (isSelected ? <CheckSquare className="h-4 w-4 shrink-0 text-primary" /> : <Square className="h-4 w-4 shrink-0 text-muted-foreground" />) : <MessageCircle className={cn("h-4 w-4 shrink-0", isActive ? "text-primary" : "text-muted-foreground")} />}
                                {isSidebarOpen && (<>
                                  <span className={cn("min-w-0 flex-1 truncate", isActive && "text-primary")}>{getConversationTitle(conversation.title)}</span>
                                  {!isSelectionMode && <button type="button" onClick={(e) => handleDeleteChat(e, conversation.id)} className="opacity-0 transition-opacity group-hover:opacity-100" title="删除会话"><Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" /></button>}
                                </>)}
                              </div>
                            </motion.div>
                          )
                        })}
                      </div>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </div>

            <div className="border-t border-border/70 px-3 py-3">
              <div className="space-y-1">
                <div className={cn("flex items-center gap-1", !isSidebarOpen && "flex-col")}>
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full" onClick={() => openSettings("general")} title="系统设置"><Settings2 className="h-4 w-4 shrink-0" /></Button>
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full" onClick={toggleTheme} title={theme === "dark" ? "浅色模式" : "深色模式"}>
                    {theme === "dark" ? <Sun className="h-4 w-4 shrink-0" /> : <Moon className="h-4 w-4 shrink-0" />}
                  </Button>
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full" onClick={() => setIsSidebarOpen((v) => !v)} title={isSidebarOpen ? "收起侧栏" : "展开侧栏"}>
                    {isSidebarOpen ? <PanelLeftClose className="h-4 w-4 shrink-0" /> : <PanelLeftOpen className="h-4 w-4 shrink-0" />}
                  </Button>
                </div>
              </div>
              <div className="mt-3 rounded-[24px] border border-border/70 bg-card/90 p-2 dark:bg-secondary/40">
                <div className={cn("flex items-center gap-3", !isSidebarOpen && "justify-center")}>
                  <Avatar className="h-9 w-9"><AvatarImage src={user?.avatar_url} /><AvatarFallback>{userInitial}</AvatarFallback></Avatar>
                  {isSidebarOpen && (<>
                    <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{userDisplayName}</p><p className="truncate text-xs text-muted-foreground">{user?.email || "已登录工作区"}</p></div>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={handleLogout} title="退出登录"><LogOut className="h-4 w-4" /></Button>
                  </>)}
                </div>
              </div>
            </div>
          </motion.aside>

          {/* =========== MAIN CONTENT =========== */}
          <motion.main layout transition={APP_SPRING} className="flex min-w-0 flex-1 flex-col overflow-hidden bg-background">
            {!isChatRoute && (
              <header className="flex h-12 items-center justify-between border-b border-border/70 bg-background/85 px-5 backdrop-blur">
                <div className="flex min-w-0 items-center gap-2">
                  <span className="truncate text-sm font-medium text-foreground">{pageMeta.title}</span>
                  <span className="hidden text-xs text-muted-foreground md:inline">{pageMeta.description}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="icon" onClick={() => openSettings("data")} title="数据设置"><Search className="h-4 w-4" /></Button>
                  <Button variant="ghost" size="icon" onClick={() => openSettings("general")} title="系统设置"><Settings2 className="h-4 w-4" /></Button>
                </div>
              </header>
            )}

            <AnimatePresence mode="wait" initial={false}>
              <motion.div key={routeBase} variants={pageVariants} initial="initial" animate="animate" exit="exit"
                transition={shouldReduceMotion ? { duration: 0.12 } : GENTLE_SPRING} className="min-h-0 flex-1 will-change-transform">
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </motion.main>
        </div>
      </LayoutGroup>

      {/* =========== SETTINGS DIALOG =========== */}
      <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
        <DialogContent className="max-w-[760px] gap-0 overflow-hidden p-0">
          <div className="grid h-[520px] md:grid-cols-[196px_minmax(0,1fr)]">
            {/* left tabs */}
            <aside className="flex h-full flex-col border-b border-border/70 bg-secondary/70 p-4 md:border-b-0 md:border-r">
              <DialogHeader className="pb-4 text-left">
                <DialogTitle>系统设置</DialogTitle>
                <DialogDescription>管理 LLM、账号与偏好。</DialogDescription>
              </DialogHeader>
              <div className="space-y-1">
                {SETTINGS_TABS.map((tab) => {
                  const Icon = tab.icon
                  const isActive = settingsTab === tab.key
                  return (
                    <button key={tab.key} type="button" onClick={() => setSettingsTab(tab.key)}
                      className={cn("flex w-full items-center gap-2 rounded-2xl px-3 py-2 text-sm transition-all duration-200", isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-background hover:text-foreground")}>
                      <Icon className="h-4 w-4" /><span>{tab.label}</span>
                    </button>
                  )
                })}
              </div>
            </aside>

            {/* right content — fixed height + scroll */}
            <div className="flex h-full min-h-0 flex-col">
              <div className="shrink-0 border-b border-border/70 px-6 py-4">
                <p className="text-sm font-medium">{SETTINGS_TABS.find((t) => t.key === settingsTab)?.label}</p>
              </div>
              <ScrollArea className="min-h-0 flex-1">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={settingsTab}
                    variants={TAB_SWITCH}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                    transition={shouldReduceMotion ? { duration: 0.1 } : GENTLE_SPRING}
                    className="px-6 py-5"
                  >
                {/* =========== GENERAL =========== */}
                {settingsTab === "general" && (
                  <div className="space-y-8">
                    {/* Theme */}
                    <section className="space-y-3">
                      <p className="text-sm font-medium">主题</p>
                      <div className="grid gap-3 sm:grid-cols-2">
                        {[
                          { key: "light" as const, label: "浅色模式", icon: Sun },
                          { key: "dark" as const, label: "深色模式", icon: Moon },
                        ].map(({ key, label, icon: Icon }) => (
                          <button key={key} type="button" onClick={() => setTheme(key)}
                            className={cn("rounded-[22px] border px-4 py-4 text-left transition-colors", theme === key ? "border-[#b7c8fe] bg-primary/10" : "border-border/80 hover:bg-secondary")}>
                            <div className="mb-3 flex items-center justify-between">
                              <Icon className="h-4 w-4 text-muted-foreground" />
                              {theme === key && <CheckSquare className="h-4 w-4 text-primary" />}
                            </div>
                            <p className="text-sm font-medium">{label}</p>
                          </button>
                        ))}
                      </div>
                    </section>

                    {/* Language */}
                    <section className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium">语言</p>
                        <p className="text-xs text-muted-foreground">界面文案与回复偏好。</p>
                      </div>
                      <div className="flex items-center gap-2 rounded-full border border-border/80 px-3 py-2 text-sm">
                        <Languages className="h-4 w-4 text-muted-foreground" />
                        <select value={language} onChange={(e) => setLanguage(e.target.value)} className="bg-transparent text-foreground outline-none">
                          <option value="zh-CN">简体中文</option>
                          <option value="en-US">English</option>
                        </select>
                      </div>
                    </section>

                    {/* LLM 配置：通过 .env / config.yaml 全局管理，无需在 UI 中修改 */}
                  </div>
                )}

                {/* =========== ACCOUNT =========== */}
                {settingsTab === "account" && (
                  <div className="space-y-6">
                    {/* Account info */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between rounded-[22px] border border-border/80 px-4 py-3">
                        <div><p className="text-sm font-medium">当前账号</p><p className="text-xs text-muted-foreground">{userDisplayName}</p></div>
                        <span className="text-sm text-muted-foreground">{user?.email}</span>
                      </div>
                      <div className="flex items-center justify-between rounded-[22px] border border-border/80 px-4 py-3">
                        <div><p className="text-sm font-medium">权限</p></div>
                        <span className="text-sm text-muted-foreground">{user?.is_superuser ? "管理员" : "普通用户"}</span>
                      </div>
                    </div>

                    {/* Password change */}
                    <div className="space-y-4 rounded-[22px] border border-border/80 p-4">
                      <div><p className="text-sm font-medium">修改密码</p><p className="text-xs text-muted-foreground">输入当前密码并设置新密码。</p></div>
                      <div className="space-y-3">
                        <div className="relative">
                          <Input type={showOldPw ? "text" : "password"} value={pwOld} onChange={(e) => setPwOld(e.target.value)} placeholder="当前密码" />
                          <button type="button" onClick={() => setShowOldPw(!showOldPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                            {showOldPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </button>
                        </div>
                        <div className="relative">
                          <Input type={showNewPw ? "text" : "password"} value={pwNew} onChange={(e) => setPwNew(e.target.value)} placeholder="新密码（至少 6 位）" />
                          <button type="button" onClick={() => setShowNewPw(!showNewPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                            {showNewPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </button>
                        </div>
                        <div className="relative">
                          <Input type={showConfirmPw ? "text" : "password"} value={pwConfirm} onChange={(e) => setPwConfirm(e.target.value)} placeholder="确认新密码" />
                          <button type="button" onClick={() => setShowConfirmPw(!showConfirmPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                            {showConfirmPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </button>
                        </div>
                      </div>
                      {pwError && <p className="text-xs text-destructive">{pwError}</p>}
                      {pwSuccess && <p className="text-xs text-green-600">{pwSuccess}</p>}
                      <Button size="sm" onClick={handlePasswordChange} disabled={pwLoading} className="gap-1.5">
                        {pwLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Key className="h-3.5 w-3.5" />}
                        修改密码
                      </Button>
                    </div>

                    {/* Logout */}
                    <Button variant="outline" className="border-destructive/30 text-destructive hover:bg-destructive/5" onClick={handleLogout}>
                      <LogOut className="mr-2 h-4 w-4" />退出登录
                    </Button>
                  </div>
                )}

                {/* =========== DATA =========== */}
                {settingsTab === "data" && (
                  <div className="space-y-6">
                    <section className="space-y-3">
                      <div><p className="text-sm font-medium">默认资料来源</p><p className="text-xs text-muted-foreground">控制回答偏向知识库、网络或自动选择。</p></div>
                      <div className="flex flex-wrap gap-2">
                        {SOURCE_OPTIONS.map((opt) => (
                          <button key={opt.key} type="button" onClick={() => setSourcePreference(opt.key)}
                            className={cn("rounded-full border px-4 py-2 text-sm transition-colors", sourcePreference === opt.key ? "border-[#b7c8fe] bg-primary/10 text-primary" : "border-border/80 text-foreground hover:bg-secondary")}>{opt.label}</button>
                        ))}
                      </div>
                    </section>
                    <section className="space-y-3">
                      <div><p className="text-sm font-medium">回答展示</p><p className="text-xs text-muted-foreground">精简摘要或展开细节。</p></div>
                      <div className="flex flex-wrap gap-2">
                        {SUMMARY_OPTIONS.map((opt) => (
                          <button key={opt.key} type="button" onClick={() => setSummaryStyle(opt.key)}
                            className={cn("rounded-full border px-4 py-2 text-sm transition-colors", summaryStyle === opt.key ? "border-[#b7c8fe] bg-primary/10 text-primary" : "border-border/80 text-foreground hover:bg-secondary")}>{opt.label}</button>
                        ))}
                      </div>
                    </section>
                    <section className="flex items-center justify-between rounded-[22px] border border-border/80 px-4 py-4">
                      <div><p className="text-sm font-medium">自动展开来源面板</p><p className="text-xs text-muted-foreground">收到来源后自动打开参考面板。</p></div>
                      <button type="button" onClick={() => setAutoOpenSources((v) => !v)}
                        className={cn("relative h-7 w-12 rounded-full transition-colors", autoOpenSources ? "bg-primary" : "bg-border")}>
                        <span className={cn("absolute top-1 h-5 w-5 rounded-full bg-white transition-transform", autoOpenSources ? "translate-x-6" : "translate-x-1")} />
                      </button>
                    </section>
                  </div>
                )}

                {/* =========== POLICY =========== */}
                {settingsTab === "policy" && (
                  <div className="space-y-3">
                    {[
                      { key: "terms", title: "服务协议", desc: "Geo-Agent 使用条款与条件。" },
                      { key: "privacy", title: "隐私说明", desc: "我们如何收集、使用和保护你的数据。" },
                      { key: "sources", title: "数据来源说明", desc: "知识库数据的来源与引用规范。" },
                    ].map(({ key, title, desc }) => (
                      <div key={key} className="flex items-center justify-between rounded-[22px] border border-border/80 px-4 py-4">
                        <div><p className="text-sm font-medium">{title}</p><p className="text-xs text-muted-foreground">{desc}</p></div>
                        <Button variant="ghost" size="sm" className="h-8 px-3" onClick={() => setPolicyView(key)}>查看</Button>
                      </div>
                    ))}
                  </div>
                )}
                  </motion.div>
                </AnimatePresence>
              </ScrollArea>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* =========== POLICY VIEWER DIALOG =========== */}
      <Dialog open={!!policyView} onOpenChange={(open) => { if (!open) setPolicyView(null) }}>
        <DialogContent className="max-w-[620px] max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>
              {policyView === "terms" ? "服务协议" : policyView === "privacy" ? "隐私说明" : "数据来源说明"}
            </DialogTitle>
            <DialogDescription>最后更新：2026 年 1 月</DialogDescription>
          </DialogHeader>
          <ScrollArea className="max-h-[60vh] pr-2">
            <div className="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed space-y-4">
              {policyView === "terms" && <TermsContent />}
              {policyView === "privacy" && <PrivacyContent />}
              {policyView === "sources" && <SourcesContent />}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </>
  )
}

/* =========== Policy Content Components =========== */

function TermsContent() {
  return (
    <>
      <h3 className="text-base font-semibold">Geo-Agent 服务协议</h3>
      <p>欢迎使用 Geo-Agent（以下简称"本服务"）。本协议是你与 Geo-Agent 开发团队之间关于使用本服务的法律协议。请仔细阅读以下条款。</p>

      <h4 className="text-sm font-semibold">1. 服务说明</h4>
      <p>Geo-Agent 是一个基于 AI 的地质智能问答系统，提供知识库检索、智能对话、知识库管理等功能。本服务通过检索增强生成（RAG）技术，结合用户上传的文件资料和公开网络信息，为用户提供地质学领域的专业问答。</p>

      <h4 className="text-sm font-semibold">2. 用户责任</h4>
      <p>你同意：不利用本服务从事任何违法活动；不上传包含恶意代码、病毒或其他有害内容的文件；不尝试未经授权访问本服务的后端系统或数据库；不通过自动化脚本或爬虫大量请求本服务接口；对你上传的文件内容拥有合法权利或已获得必要授权。</p>

      <h4 className="text-sm font-semibold">3. 免责声明</h4>
      <p>本服务提供的 AI 生成内容仅供参考，不构成专业地质学建议。对于因使用本服务提供的信息而产生的任何决策或后果，开发团队不承担法律责任。本服务可能因维护、网络故障或其他原因中断，开发团队不保证服务的持续可用性。</p>

      <h4 className="text-sm font-semibold">4. 知识产权</h4>
      <p>Geo-Agent 系统的代码、界面设计和品牌标识归开发团队所有。用户上传的文件资料的知识产权归原作者或上传者所有。AI 生成内容的版权归属遵循相关法律法规。</p>

      <h4 className="text-sm font-semibold">5. 协议修改</h4>
      <p>我们保留随时修改本协议的权利，修改后的协议将在本页面公布。继续使用本服务即表示你接受修改后的条款。</p>
    </>
  )
}

function PrivacyContent() {
  return (
    <>
      <h3 className="text-base font-semibold">隐私说明</h3>
      <p>Geo-Agent 重视你的隐私。本隐私说明解释了我们如何收集、使用和保护你的个人信息。</p>

      <h4 className="text-sm font-semibold">1. 信息收集</h4>
      <p>我们收集以下信息：<strong>账号信息</strong>——注册时提供的用户名、邮箱地址和加密存储的密码；<strong>使用数据</strong>——对话记录、搜索历史、上传的文件；<strong>设备信息</strong>——浏览器类型、IP 地址、访问时间等日志数据。</p>

      <h4 className="text-sm font-semibold">2. 信息使用</h4>
      <p>我们使用收集的信息用于：提供和改进本服务的功能；处理你的请求并生成 AI 回复；维护系统安全、排查故障；遵守法律法规的要求。我们不会将你的个人信息出售给第三方。</p>

      <h4 className="text-sm font-semibold">3. 数据存储与安全</h4>
      <p>你的账号信息存储在加密的 MySQL 数据库中，密码使用 bcrypt 哈希存储。对话记录和文件数据保存在服务器本地。我们采取合理的技术措施保护你的数据安全，但无法保证绝对的安全。</p>

      <h4 className="text-sm font-semibold">4. Cookie 使用</h4>
      <p>本服务使用必要的 Cookie 来维持登录状态和保存界面偏好设置（如主题模式）。我们不会使用 Cookie 进行跨站追踪。</p>

      <h4 className="text-sm font-semibold">5. 数据删除</h4>
      <p>你可以随时删除自己的对话记录和上传的文件。如需彻底删除账号及所有关联数据，请联系管理员。我们将在验证身份后的 30 个工作日内处理你的请求。</p>

      <h4 className="text-sm font-semibold">6. 第三方服务</h4>
      <p>本服务使用第三方 AI 模型提供商（如 SiliconFlow、OpenAI 等）来处理你的请求。你在系统设置中配置的 API Key 仅存储在你的账号偏好中，不会与模型提供商以外的第三方共享。</p>
    </>
  )
}

function SourcesContent() {
  return (
    <>
      <h3 className="text-base font-semibold">数据来源说明</h3>
      <p>Geo-Agent 的知识库数据来自多个渠道，我们致力于确保数据的准确性和合规性。</p>

      <h4 className="text-sm font-semibold">1. 用户上传文件</h4>
      <p>用户可以通过文件管理功能上传 PDF、Word、Markdown、TXT 等格式的文件资料。上传的文件经文本提取和向量化处理后存入知识库。用户应确保上传内容不侵犯第三方知识产权。</p>

      <h4 className="text-sm font-semibold">2. 公开学术资源</h4>
      <p>系统预置知识库可能包含来自公开学术数据库（如 CNKI、万方、维普等）的文件摘要和元数据。这些内容仅用于检索增强生成，不提供全文下载。</p>

      <h4 className="text-sm font-semibold">3. 网络实时信息</h4>
      <p>当启用网络搜索功能时，系统通过第三方搜索 API（如 Tavily）获取公开的网页信息。搜索结果仅用于增强回答的时效性，系统不会缓存或重新分发完整的网页内容。</p>

      <h4 className="text-sm font-semibold">4. AI 生成内容</h4>
      <p>AI 生成的回答基于检索到的文件片段和网络信息，结合大语言模型的知识生成。AI 生成的内容可能包含不准确的信息，请在使用前进行核实。</p>

      <h4 className="text-sm font-semibold">5. 引用规范</h4>
      <p>在 RAG 模式下，AI 回答会标注引用的文件来源。用户如需引用本系统提供的信息，建议追溯到原始文件进行核实，并按照学术规范引用原始出处。</p>
    </>
  )
}
