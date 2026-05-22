import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useI18nStore } from "@/i18n"
import { getPolicyDocument, type PolicyKey } from "@/i18n/policyContent"
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

export default function Layout() {
  const t = useI18nStore((s) => s.t)
  const language = useI18nStore((s) => s.language)
  const i18nLoading = useI18nStore((s) => s.loading)
  const setLanguage = useI18nStore((s) => s.setLanguage)

  // BUG-3: module-level → component scope, reacts to language changes
  const NAV_ITEMS = useMemo(() => [
    { to: "/chat", match: "/chat", labelKey: "nav.chat" as const, icon: MessageSquare },
    { to: "/documents", match: "/documents", labelKey: "nav.documents" as const, icon: FileText },
  ], [])

  const SETTINGS_TABS: Array<{ key: SettingsTab; label: string; icon: typeof Sparkles }> = useMemo(() => [
    { key: "general", label: t("settings.general"), icon: Sparkles },
    { key: "account", label: t("settings.account"), icon: Shield },
    { key: "data", label: t("settings.data"), icon: BookOpen },
    { key: "policy", label: t("settings.policy"), icon: FileText },
  ], [t])

  const SOURCE_OPTIONS = useMemo(() => [
    { key: "knowledge" as const, label: t("settings.sourceKnowledge") },
    { key: "web" as const, label: t("settings.sourceWeb") },
    { key: "auto" as const, label: t("settings.sourceAuto") },
  ], [t])

  const SUMMARY_OPTIONS = useMemo(() => [
    { key: "concise" as const, label: t("settings.summaryConcise") },
    { key: "expanded" as const, label: t("settings.summaryExpanded") },
  ], [t])

  const pageMetaTitle = useMemo(() => t("documents.title"), [t])
  const pageMetaDesc = useMemo(() => t("documents.desc"), [t])
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

  const conversationTitle = useCallback((title?: string | null) => {
    if (!title) return t("nav.newChat")
    const text = title.trim()
    if (!text) return t("nav.newChat")
    return text.length > 26 ? `${text.slice(0, 26)}...` : text
  }, [t])

  const conversationGroupLabel = useCallback((updatedAt: string) => {
    const updated = new Date(updatedAt)
    const now = new Date()
    const diffDays = Math.floor((now.getTime() - updated.getTime()) / 86400000)
    if (updated.toDateString() === now.toDateString()) return t("nav.today")
    if (diffDays <= 7) return t("nav.recent7")
    return t("nav.earlier")
  }, [t])

  const groupOrder = useMemo(
    () => [t("nav.today"), t("nav.recent7"), t("nav.earlier")],
    [t, language]
  )

  const groupedConversations = useMemo(() => {
    const groups = new Map<string, typeof conversations>()
    conversations.forEach((conversation) => {
      const label = conversationGroupLabel(conversation.updated_at)
      const current = groups.get(label) ?? []
      current.push(conversation)
      groups.set(label, current)
    })
    return groupOrder
      .map((label) => ({ label, items: groups.get(label) ?? [] }))
      .filter((group) => group.items.length > 0)
  }, [conversations, conversationGroupLabel, groupOrder])

  // ---------- effects ----------
  useEffect(() => { if (user) loadConversations() }, [loadConversations, user])

  useEffect(() => {
    document.documentElement.lang = language === "zh-CN" ? "zh-CN" : "en"
    document.title = language === "zh-CN" ? "地质文献智能体" : "Geo-Agent"
  }, [language])

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
    if (window.confirm(t("nav.deleteConversationConfirm"))) {
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
    if (window.confirm(t("nav.deleteConversationBatchConfirm", { count: selectedConversationIds.size }))) {
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
    if (pwNew.length < 6 || pwConfirm.length < 6) { setPwError(t("nav.passwordMinLength")); return }
    if (pwNew !== pwConfirm) { setPwError(t("settings.passwordMismatch")); return }
    setPwLoading(true)
    try {
      await authService.changePassword({ old_password: pwOld, new_password: pwNew, confirm_password: pwConfirm })
      setPwSuccess(t("settings.passwordSuccess"))
      setPwOld(""); setPwNew(""); setPwConfirm("")
    } catch (err: any) {
      setPwError(err?.response?.data?.detail || t("nav.changePasswordFailed"))
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
                <span className="flex items-center gap-2"><Plus className="h-4 w-4" />{isSidebarOpen && <span>{t("nav.newChat")}</span>}</span>
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
                        <Icon className="h-4 w-4 shrink-0" />{isSidebarOpen && <span>{t(item.labelKey)}</span>}
                      </span>
                    </Link>
                  </Button>
                )
              })}
            </nav>

            <div className="mt-4 flex min-h-0 flex-1 flex-col">
              {isSidebarOpen && (
                <div className="flex items-center justify-between px-4 pb-2">
                  <p className="text-xs text-muted-foreground">{t("nav.history")}</p>
                  {conversations.length > 0 && (
                    <div className="flex items-center gap-1">
                      {isSelectionMode && (<>
                        <Button variant="ghost" size="icon" className="h-7 w-7"
                          onClick={() => selectedConversationIds.size === conversations.length ? (clearSelection(), setSelectionMode(true)) : selectAllConversations()}
                          title={selectedConversationIds.size === conversations.length ? t("nav.deselectAll") : t("nav.selectAll")}>
                          {selectedConversationIds.size === conversations.length ? <CheckCheck className="h-3.5 w-3.5" /> : <CheckSquare className="h-3.5 w-3.5" />}
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive" disabled={selectedConversationIds.size === 0} onClick={handleBatchDelete} title={t("nav.deleteSelected")}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </>)}
                      <Button variant={isSelectionMode ? "secondary" : "ghost"} size="sm" className="h-7 px-2.5"
                        onClick={() => isSelectionMode ? clearSelection() : setSelectionMode(true)}>
                        {isSelectionMode ? t("nav.cancel") : t("nav.manage")}
                      </Button>
                    </div>
                  )}
                </div>
              )}
              <ScrollArea className="min-h-0 flex-1 px-2">
                {groupedConversations.length === 0 ? (
                  <div className={cn("px-2 py-6 text-center text-xs text-muted-foreground", !isSidebarOpen && "px-0")}>{isSidebarOpen ? t("nav.noHistory") : "—"}</div>
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
                              title={conversation.title || t("nav.newChat")}>
                              {isActive && <motion.span layoutId="conversation-active" transition={SOFT_SPRING} className="absolute inset-0 rounded-2xl border border-[#b7c8fe] bg-primary/10 dark:border-[#3c4f8d] dark:bg-[#1f2942]" />}
                              <div className={cn("relative flex w-full items-center gap-2", !isSidebarOpen && "justify-center")}>
                                {isSelectionMode ? (isSelected ? <CheckSquare className="h-4 w-4 shrink-0 text-primary" /> : <Square className="h-4 w-4 shrink-0 text-muted-foreground" />) : <MessageCircle className={cn("h-4 w-4 shrink-0", isActive ? "text-primary" : "text-muted-foreground")} />}
                                {isSidebarOpen && (<>
                                  <span className={cn("min-w-0 flex-1 truncate", isActive && "text-primary")}>{conversationTitle(conversation.title)}</span>
                                  {!isSelectionMode && <button type="button" onClick={(e) => handleDeleteChat(e, conversation.id)} className="opacity-0 transition-opacity group-hover:opacity-100" title={t("nav.deleteConversationTitle")}><Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" /></button>}
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
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full" onClick={() => openSettings("general")} title={t("settings.title")}><Settings2 className="h-4 w-4 shrink-0" /></Button>
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full" onClick={toggleTheme} title={theme === "dark" ? t("settings.lightMode") : t("settings.darkMode")}>
                    {theme === "dark" ? <Sun className="h-4 w-4 shrink-0" /> : <Moon className="h-4 w-4 shrink-0" />}
                  </Button>
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full" onClick={() => setIsSidebarOpen((v) => !v)} title={isSidebarOpen ? t("nav.collapse") : t("nav.expand")}>
                    {isSidebarOpen ? <PanelLeftClose className="h-4 w-4 shrink-0" /> : <PanelLeftOpen className="h-4 w-4 shrink-0" />}
                  </Button>
                </div>
              </div>
              <div className="mt-3 rounded-[24px] border border-border/70 bg-card/90 p-2 dark:bg-secondary/40">
                <div className={cn("flex items-center gap-3", !isSidebarOpen && "justify-center")}>
                  <Avatar className="h-9 w-9"><AvatarImage src={user?.avatar_url} /><AvatarFallback>{userInitial}</AvatarFallback></Avatar>
                  {isSidebarOpen && (<>
                    <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{userDisplayName}</p><p className="truncate text-xs text-muted-foreground">{user?.email || t("common.loggedIn")}</p></div>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={handleLogout} title={t("settings.logout")}><LogOut className="h-4 w-4" /></Button>
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
                  <span className="truncate text-sm font-medium text-foreground">{pageMetaTitle}</span>
                  <span className="hidden text-xs text-muted-foreground md:inline">{pageMetaDesc}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="icon" onClick={() => openSettings("data")} title={t("nav.dataSettings")}><Search className="h-4 w-4" /></Button>
                  <Button variant="ghost" size="icon" onClick={() => openSettings("general")} title={t("settings.title")}><Settings2 className="h-4 w-4" /></Button>
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
                <DialogTitle>{t("settings.title")}</DialogTitle>
                <DialogDescription>{t("settings.desc")}</DialogDescription>
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
                      <p className="text-sm font-medium">{t("settings.theme")}</p>
                      <div className="grid gap-3 sm:grid-cols-2">
                        {[
                          { key: "light" as const, label: t("settings.lightMode"), icon: Sun },
                          { key: "dark" as const, label: t("settings.darkMode"), icon: Moon },
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
                        <p className="text-sm font-medium">{t("settings.language")}</p>
                        <p className="text-xs text-muted-foreground">{t("settings.languageDesc")}</p>
                      </div>
                      <div className="flex items-center gap-2 rounded-full border border-border/80 px-3 py-2 text-sm">
                        <Languages className="h-4 w-4 text-muted-foreground" />
                        <select
                          value={language}
                          disabled={i18nLoading}
                          onChange={(e) => void setLanguage(e.target.value as "en" | "zh-CN")}
                          className="bg-transparent text-foreground outline-none disabled:opacity-50"
                        >
                          <option value="zh-CN">{t("settings.chinese")}</option>
                          <option value="en">English</option>
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
                        <div><p className="text-sm font-medium">{t("settings.currentAccount")}</p><p className="text-xs text-muted-foreground">{userDisplayName}</p></div>
                        <span className="text-sm text-muted-foreground">{user?.email}</span>
                      </div>
                      <div className="flex items-center justify-between rounded-[22px] border border-border/80 px-4 py-3">
                        <div><p className="text-sm font-medium">{t("settings.role")}</p></div>
                        <span className="text-sm text-muted-foreground">{user?.is_superuser ? t("settings.admin") : t("settings.user")}</span>
                      </div>
                    </div>

                    {/* Password change */}
                    <div className="space-y-4 rounded-[22px] border border-border/80 p-4">
                      <div><p className="text-sm font-medium">{t("settings.changePassword")}</p><p className="text-xs text-muted-foreground">{t("settings.changePasswordDesc")}</p></div>
                      <div className="space-y-3">
                        <div className="relative">
                          <Input type={showOldPw ? "text" : "password"} value={pwOld} onChange={(e) => setPwOld(e.target.value)} placeholder={t("settings.oldPassword")} />
                          <button type="button" onClick={() => setShowOldPw(!showOldPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                            {showOldPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </button>
                        </div>
                        <div className="relative">
                          <Input type={showNewPw ? "text" : "password"} value={pwNew} onChange={(e) => setPwNew(e.target.value)} placeholder={t("settings.newPassword")} />
                          <button type="button" onClick={() => setShowNewPw(!showNewPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                            {showNewPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </button>
                        </div>
                        <div className="relative">
                          <Input type={showConfirmPw ? "text" : "password"} value={pwConfirm} onChange={(e) => setPwConfirm(e.target.value)} placeholder={t("settings.confirmNewPassword")} />
                          <button type="button" onClick={() => setShowConfirmPw(!showConfirmPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                            {showConfirmPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </button>
                        </div>
                      </div>
                      {pwError && <p className="text-xs text-destructive">{pwError}</p>}
                      {pwSuccess && <p className="text-xs text-green-600">{pwSuccess}</p>}
                      <Button size="sm" onClick={handlePasswordChange} disabled={pwLoading} className="gap-1.5">
                        {pwLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Key className="h-3.5 w-3.5" />}
                        {t("settings.changePasswordBtn")}
                      </Button>
                    </div>

                    {/* Logout */}
                    <Button variant="outline" className="border-destructive/30 text-destructive hover:bg-destructive/5" onClick={handleLogout}>
                      <LogOut className="mr-2 h-4 w-4" />{t("settings.logout")}
                    </Button>
                  </div>
                )}

                {/* =========== DATA =========== */}
                {settingsTab === "data" && (
                  <div className="space-y-6">
                    <section className="space-y-3">
                      <div><p className="text-sm font-medium">{t("settings.sourceDefault")}</p><p className="text-xs text-muted-foreground">{t("settings.sourceDescLong")}</p></div>
                      <div className="flex flex-wrap gap-2">
                        {SOURCE_OPTIONS.map((opt) => (
                          <button key={opt.key} type="button" onClick={() => setSourcePreference(opt.key)}
                            className={cn("rounded-full border px-4 py-2 text-sm transition-colors", sourcePreference === opt.key ? "border-[#b7c8fe] bg-primary/10 text-primary" : "border-border/80 text-foreground hover:bg-secondary")}>{opt.label}</button>
                        ))}
                      </div>
                    </section>
                    <section className="space-y-3">
                      <div><p className="text-sm font-medium">{t("settings.summaryStyle")}</p><p className="text-xs text-muted-foreground">{t("settings.summaryDesc")}</p></div>
                      <div className="flex flex-wrap gap-2">
                        {SUMMARY_OPTIONS.map((opt) => (
                          <button key={opt.key} type="button" onClick={() => setSummaryStyle(opt.key)}
                            className={cn("rounded-full border px-4 py-2 text-sm transition-colors", summaryStyle === opt.key ? "border-[#b7c8fe] bg-primary/10 text-primary" : "border-border/80 text-foreground hover:bg-secondary")}>{opt.label}</button>
                        ))}
                      </div>
                    </section>
                    <section className="flex items-center justify-between rounded-[22px] border border-border/80 px-4 py-4">
                      <div><p className="text-sm font-medium">{t("settings.autoOpenSources")}</p><p className="text-xs text-muted-foreground">{t("settings.autoOpenSourcesDesc")}</p></div>
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
                      { key: "terms", title: t("policy.terms"), desc: t("policy.termsDesc") },
                      { key: "privacy", title: t("policy.privacy"), desc: t("policy.privacyDesc") },
                      { key: "sources", title: t("policy.sources"), desc: t("policy.sourcesDesc") },
                    ].map(({ key, title, desc }) => (
                      <div key={key} className="flex items-center justify-between rounded-[22px] border border-border/80 px-4 py-4">
                        <div><p className="text-sm font-medium">{title}</p><p className="text-xs text-muted-foreground">{desc}</p></div>
                        <Button variant="ghost" size="sm" className="h-8 px-3" onClick={() => setPolicyView(key)}>{t("settings.viewPolicy")}</Button>
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
              {policyView === "terms" ? t("policy.terms") : policyView === "privacy" ? t("policy.privacy") : t("policy.sources")}
            </DialogTitle>
            <DialogDescription>{t("settings.policyUpdated")}</DialogDescription>
          </DialogHeader>
          <ScrollArea className="max-h-[60vh] pr-2">
            <div className="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed space-y-4">
              {policyView === "terms" && <PolicyDocumentContent policyKey="terms" />}
              {policyView === "privacy" && <PolicyDocumentContent policyKey="privacy" />}
              {policyView === "sources" && <PolicyDocumentContent policyKey="sources" />}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </>
  )
}

/* =========== Policy Content =========== */

function PolicyDocumentContent({ policyKey }: { policyKey: PolicyKey }) {
  const language = useI18nStore((s) => s.language)
  const doc = getPolicyDocument(language, policyKey)

  return (
    <>
      <h3 className="text-base font-semibold">{doc.title}</h3>
      <p>{doc.intro}</p>
      {doc.sections.map((section) => (
        <div key={section.heading}>
          <h4 className="text-sm font-semibold">{section.heading}</h4>
          <p>{section.body}</p>
        </div>
      ))}
    </>
  )
}
