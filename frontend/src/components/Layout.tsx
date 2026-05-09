import { useEffect, useState } from "react"
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom"
import { AnimatePresence, motion } from "framer-motion"
import { useAuthStore } from "../store/useAuthStore"
import { useChatStore } from "../store/useChatStore"
import { useThemeStore } from "../store/useThemeStore"
import { useRouteStore } from "../store/useRouteStore"
import { Button } from "./ui/button"
import {
  CheckCheck,
  CheckSquare,
  FileText,
  Globe2,
  MessageCircle,
  MessageSquare,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Settings2,
  Square,
  Trash2,
} from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar"
import { ScrollArea } from "./ui/scroll-area"
import { cn } from "@/lib/utils"

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user } = useAuthStore()
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
  const { theme, toggleTheme } = useThemeStore()
  const { setLastRoute } = useRouteStore()
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  const routeBase = "/" + location.pathname.split("/")[1]

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

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      <aside
        className={cn(
          "flex h-full shrink-0 flex-col border-r border-border bg-muted/40 transition-all duration-200",
          isSidebarOpen ? "w-[272px]" : "w-[72px]"
        )}
      >
        <div className="relative flex items-center justify-between px-4 pb-3 pt-5">
          <div className={cn("flex min-w-0 items-center gap-2.5", !isSidebarOpen && "justify-center")}>
            <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-border bg-card text-primary">
              <Globe2 className="h-4 w-4" aria-hidden="true" />
            </div>
            {isSidebarOpen && (
              <div className="min-w-0">
                <p className="truncate text-[17px] font-semibold text-primary">Geo-Agent</p>
                <p className="truncate text-[13px] text-muted-foreground">地质文献智能体</p>
              </div>
            )}
          </div>

          <button
            onClick={() => setIsSidebarOpen((prev) => !prev)}
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
              !isSidebarOpen && "mx-auto"
            )}
            title={isSidebarOpen ? "收起侧边栏" : "展开侧边栏"}
          >
            {isSidebarOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
          </button>
        </div>

        <div className="px-4 pb-4">
          <button
            onClick={handleNewChat}
            className={cn(
              "flex w-full items-center rounded-xl border border-border bg-card text-left text-foreground transition-colors hover:bg-accent/45",
              isSidebarOpen ? "gap-2.5 px-3.5 py-2.5" : "justify-center px-0 py-2.5"
            )}
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/12 text-primary">
              <Plus className="h-3.5 w-3.5" />
            </div>
            {isSidebarOpen && (
              <div className="min-w-0">
                <div className="text-[14px] font-semibold">开启新对话</div>
              </div>
            )}
          </button>
        </div>

        <nav className="px-3 pb-3">
          <div className="flex flex-col gap-1">
            <Link
              to="/chat"
              className={cn("nav-pill flex items-center justify-center gap-3", location.pathname.startsWith("/chat") && "nav-pill-active", !isSidebarOpen && "justify-center")}
            >
              <MessageSquare className="h-4 w-4 shrink-0" />
              {isSidebarOpen && <span>智能问答</span>}
            </Link>
            <Link
              to="/documents"
              className={cn("nav-pill flex items-center justify-center gap-3", location.pathname.startsWith("/documents") && "nav-pill-active", !isSidebarOpen && "justify-center")}
            >
              <FileText className="h-4 w-4 shrink-0" />
              {isSidebarOpen && <span>文献管理</span>}
            </Link>
          </div>
        </nav>

        <div className="flex min-h-0 flex-1 flex-col border-t border-border">
          {isSidebarOpen && (
            <div className="flex items-center justify-between px-4 pb-2 pt-4">
              <div className="text-xs font-medium text-muted-foreground">今天</div>
              {conversations.length > 0 && (
                <div className="flex items-center gap-1">
                  {isSelectionMode && (
                    <>
                      <button
                        onClick={handleSelectAll}
                        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                        title={selectedConversationIds.size === conversations.length ? "取消全选" : "全选"}
                      >
                        {selectedConversationIds.size === conversations.length ? <CheckCheck className="h-4 w-4 text-primary" /> : <CheckSquare className="h-4 w-4" />}
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
                      "rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors",
                      isSelectionMode ? "bg-primary/12 text-primary" : "bg-muted text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {isSelectionMode ? "取消" : "管理"}
                  </button>
                </div>
              )}
            </div>
          )}

          <ScrollArea className="min-h-0 flex-1 px-3 pb-3">
            <div className="space-y-0.5">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  onClick={() => handleConversationClick(conv.id)}
                  className={cn(
                    "group cursor-pointer rounded-lg px-3 py-1.5 transition-colors",
                    isSidebarOpen ? "flex items-start gap-2.5" : "flex justify-center px-0",
                    currentConversationId === conv.id && !isSelectionMode
                      ? "bg-primary/12 text-primary"
                      : "text-foreground/85 hover:bg-accent",
                    isSelectionMode && selectedConversationIds.has(conv.id) && "bg-primary/12 text-primary"
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
          </ScrollArea>
        </div>

        <div className="border-t border-border px-3 py-4">
          <div className={cn("flex items-center gap-3", !isSidebarOpen && "justify-center")}>
            <Avatar className="h-9 w-9">
              <AvatarImage src={user?.avatar_url} />
              <AvatarFallback>{user?.username?.[0]?.toUpperCase()}</AvatarFallback>
            </Avatar>

            {isSidebarOpen && (
              <>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{user?.full_name || user?.username}</p>
                </div>
                <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg text-muted-foreground" onClick={toggleTheme} title="界面设置">
                  {theme === "dark" ? <Moon className="h-4 w-4" /> : <Settings2 className="h-4 w-4" />}
                </Button>
              </>
            )}
          </div>

          {!isSidebarOpen && (
            <div className="mt-3 flex flex-col items-center gap-1.5">
              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg text-muted-foreground" onClick={toggleTheme} title="界面设置">
                {theme === "dark" ? <Moon className="h-4 w-4" /> : <Settings2 className="h-4 w-4" />}
              </Button>
            </div>
          )}
        </div>
      </aside>

      <main className="relative min-w-0 flex-1 overflow-hidden bg-background">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={routeBase}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.18, ease: [0.2, 0.8, 0.2, 1] }}
            className="h-full"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}
