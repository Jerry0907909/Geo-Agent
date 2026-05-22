import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ClipboardEvent as ReactClipboardEvent,
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react"
import { useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom"
import Markdown from "react-markdown"
import { AnimatePresence, motion, useReducedMotion } from "framer-motion"
import {
  ArrowRight,
  BookOpen,
  Bot,
  Check,
  ChevronRight,
  Copy,
  Globe,
  RotateCcw,
  Search,
  Send,
  Settings2,
  X,
} from "lucide-react"
import { translateStreamStatus, useI18nStore } from "@/i18n"
import {
  chatService,
  conversationService,
  type ChatMessage,
  type ChatMode,
  type Source,
} from "@/services/api"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import ThinkingWave from "@/components/ThinkingWave"
import StreamingMessage from "@/components/StreamingMessage"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useChatStore } from "@/store/useChatStore"
import { conversationLanguage } from "@/lib/detectLanguage"
import { cn } from "@/lib/utils"
import { COLLAPSE_REVEAL, REDUCED_FADE, SOFT_SPRING, STAGGER_ITEM, STAGGER_PARENT } from "@/lib/motion"

const MODE_CONFIG = {
  chat: { labelKey: "chat.chatMode", icon: Bot },
  rag: { labelKey: "chat.ragMode", icon: Search },
}

const MAX_IMAGE_SIZE = 5 * 1024 * 1024

export default function ChatPage() {
  const t = useI18nStore((s) => s.t)
  const language = useI18nStore((s) => s.language)
  const { conversationId } = useParams<{ conversationId?: string }>()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { currentConversationId, loadConversations, setCurrentConversationId } = useChatStore()

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [sources, setSources] = useState<Source[]>([])
  const [mode, setMode] = useState<ChatMode>("chat")
  const [topK, setTopK] = useState(5)
  const [minRelevanceScore, setMinRelevanceScore] = useState(0)
  const [webSearchEnabled, setWebSearchEnabled] = useState(false)
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [streamingContent, setStreamingContent] = useState("")
  const [statusMessage, setStatusMessage] = useState("")
  const [followUpQuestions, setFollowUpQuestions] = useState<string[]>([])
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  const [expandedSourceIndex, setExpandedSourceIndex] = useState<number | null>(null)
  const [isSourcesDialogOpen, setIsSourcesDialogOpen] = useState(false)
  const [isRagSettingsOpen, setIsRagSettingsOpen] = useState(false)

  const scrollRef = useRef<HTMLDivElement>(null)
  const shouldReduceMotion = useReducedMotion()

  const markdownComponents = useMemo(
    () => ({
      p: ({ children }: { children?: React.ReactNode }) => <p className="mb-3 last:mb-0">{children}</p>,
      ul: ({ children }: { children?: React.ReactNode }) => <ul className="mb-3 list-disc space-y-1 pl-5">{children}</ul>,
      ol: ({ children }: { children?: React.ReactNode }) => <ol className="mb-3 list-decimal space-y-1 pl-5">{children}</ol>,
      li: ({ children }: { children?: React.ReactNode }) => <li className="leading-7">{children}</li>,
      code: ({ inline, children, ...props }: any) =>
        inline ? (
          <code className="rounded bg-secondary px-1.5 py-0.5 text-sm" {...props}>
            {children}
          </code>
        ) : (
          <code
            className="mb-3 block overflow-x-auto rounded-2xl border border-border/80 bg-secondary px-4 py-3 text-sm"
            {...props}
          >
            {children}
          </code>
        ),
    }),
    []
  )
  const displayStatusMessage = useCallback(
    (message: string) => translateStreamStatus(message, t),
    [t, language]
  )

  const visibleSuggestedQuestions = useMemo(
    () => [
      t("chat.suggest1"),
      t("chat.suggest2"),
      t("chat.suggest3"),
      t("chat.suggest4"),
    ],
    [t, language]
  )
  const motionListItem = shouldReduceMotion ? REDUCED_FADE : STAGGER_ITEM
  const collapseMotion = shouldReduceMotion ? REDUCED_FADE : COLLAPSE_REVEAL

  const showWelcome = !currentConversationId && messages.length === 0

  const generateFollowUpQuestions = useCallback(async (question: string, answer: string) => {
    try {
      const lang = conversationLanguage(question, answer)
      const result = await chatService.generateFollowUp(question, answer, lang)
      if (result.questions?.length) {
        setFollowUpQuestions(result.questions.slice(0, 3))
        return
      }
    } catch {
      // LLM 生成失败 → 不展示推荐问题，优于硬编码无关内容
    }
    setFollowUpQuestions([])
  }, [])

  useEffect(() => {
    const urlMode = searchParams.get("mode")
    if (urlMode === "rag" || urlMode === "chat") {
      setMode(urlMode)
    }
  }, [searchParams])

  useEffect(() => {
    const prompt = (location.state as { prompt?: string } | null)?.prompt
    if (prompt) {
      setInput(prompt)
    }
  }, [location.state])

  useEffect(() => {
    const nextParams = new URLSearchParams(searchParams)
    if (mode === "rag") {
      nextParams.set("mode", "rag")
    } else {
      nextParams.delete("mode")
    }

    if (nextParams.toString() !== searchParams.toString()) {
      setSearchParams(nextParams, { replace: true })
    }
  }, [mode, searchParams, setSearchParams])

  useEffect(() => {
    if (conversationId) {
      const id = Number.parseInt(conversationId, 10)
      if (!Number.isNaN(id)) {
        setCurrentConversationId(id)
      }
      return
    }

    setCurrentConversationId(null)
  }, [conversationId, setCurrentConversationId])

  useEffect(() => {
    let isCancelled = false

    const loadData = async () => {
      if (!currentConversationId) {
        setMessages([])
        setSources([])
        setIsLoading(false)
        setStreamingContent("")
        setStatusMessage("")
        return
      }

      try {
        setIsLoading(true)
        const data = await conversationService.getMessages(currentConversationId)
        if (isCancelled) return

        setMessages(data.messages)
        const lastAssistant = [...data.messages].reverse().find((message) => message.role === "assistant")
        setSources(lastAssistant?.metadata?.sources ?? [])
      } catch (error) {
        if (!isCancelled) {
          console.error("Failed to load messages:", error)
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false)
        }
      }
    }

    loadData()
    return () => {
      isCancelled = true
    }
  }, [currentConversationId])

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, streamingContent])

  const handleRemoveImage = () => {
    setSelectedImage(null)
    setImagePreview(null)
  }

  const handleFollowUpClick = (question: string) => {
    setInput(question)
    setFollowUpQuestions([])
    window.setTimeout(() => {
      document.querySelector("form")?.requestSubmit()
    }, 100)
  }

  const handleSubmit = useCallback(
    async (event?: FormEvent) => {
      event?.preventDefault()
      if ((!input.trim() && !selectedImage) || isLoading) return

      const imageToSend = selectedImage
      const imagePreviewToShow = imagePreview
      const userMsg: ChatMessage = {
        role: "user",
        content: input || t("chat.analyzeImagePrompt"),
        metadata: imagePreviewToShow ? { image: imagePreviewToShow } : undefined,
      }

      setMessages((previous) => [...previous, userMsg])
      setInput("")
      setSelectedImage(null)
      setImagePreview(null)
      setIsLoading(true)
      setSources([])
      setStreamingContent("")
      setStatusMessage("")
      setFollowUpQuestions([])

      try {
        let newConversationId: number | null = null
        let fullContent = ""
        let latestSources: Source[] = []
        let hasAddedPlaceholder = false

        // RAF 流式 — 节流到 60fps，始终渲染最新内容
        let rafId: number | null = null
        let latestContent = ""

        const flushStreaming = () => {
          if (rafId !== null) return
          rafId = requestAnimationFrame(() => {
            setStreamingContent(latestContent)
            rafId = null
          })
        }

        const streamPayload =
          mode === "rag"
            ? {
                message: userMsg.content,
                conversation_id: currentConversationId,
                mode,
                top_k: topK,
                min_relevance_score: minRelevanceScore,
                web_search: webSearchEnabled,
                image_base64: imageToSend,
              }
            : {
                message: userMsg.content,
                conversation_id: currentConversationId,
                mode: "chat" as const,
                web_search: webSearchEnabled,
                image_base64: imageToSend,
              }

        for await (const streamEvent of chatService.stream(streamPayload)) {
          switch (streamEvent.type) {
            case "info":
              if (streamEvent.conversation_id && !currentConversationId) {
                newConversationId = streamEvent.conversation_id
              }
              break
            case "status":
              setStatusMessage(displayStatusMessage(streamEvent.message || ""))
              break
            case "content":
              if (!hasAddedPlaceholder) {
                setMessages((previous) => [...previous, { role: "assistant", content: "" }])
                hasAddedPlaceholder = true
              }

              fullContent += streamEvent.content || ""
              latestContent = fullContent
              setStatusMessage("")
              flushStreaming()
              break
            case "sources":
              latestSources = streamEvent.sources || []
              setSources(latestSources)
              break
            case "done":
              setStatusMessage("")
              // 确保最后一帧渲染
              if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null }
              setStreamingContent(fullContent)

              if (newConversationId) {
                setCurrentConversationId(newConversationId)
                loadConversations()
                navigate(`/chat/${newConversationId}`, { replace: true })
              }

              if (fullContent) {
                setMessages((previous) => {
                  const updated = [...previous]
                  const lastIndex = updated.length - 1
                  if (lastIndex >= 0 && updated[lastIndex].role === "assistant") {
                    updated[lastIndex] = {
                      ...updated[lastIndex],
                      content: fullContent,
                      metadata: latestSources.length
                        ? { ...updated[lastIndex].metadata, sources: latestSources }
                        : updated[lastIndex].metadata,
                    }
                  }
                  return updated
                })

                generateFollowUpQuestions(userMsg.content, fullContent)
              }
              setStreamingContent("")
              break
            case "error":
              if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null }
              setStreamingContent("")
              throw new Error(streamEvent.message)
          }
        }
      } catch (error) {
        console.error("Chat failed:", error)
        setMessages((previous) => {
          const updated = [...previous]
          const lastMessage = updated[updated.length - 1]

          if (lastMessage?.role === "assistant") {
            updated[updated.length - 1] = {
              role: "assistant",
              content: t("chat.errorMessage"),
            }
          } else {
            updated.push({
              role: "assistant",
              content: t("chat.errorMessage"),
            })
          }

          return updated
        })
      } finally {
        setIsLoading(false)
        setStreamingContent("")
        setStatusMessage("")
      }
    },
    [
      currentConversationId,
      displayStatusMessage,
      generateFollowUpQuestions,
      imagePreview,
      input,
      isLoading,
      loadConversations,
      minRelevanceScore,
      mode,
      navigate,
      selectedImage,
      setCurrentConversationId,
      t,
      topK,
      webSearchEnabled,
    ]
  )

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      handleSubmit()
    }
  }

  const handlePaste = (event: ReactClipboardEvent<HTMLTextAreaElement>) => {
    const items = event.clipboardData?.items
    if (!items) return

    for (let i = 0; i < items.length; i += 1) {
      const item = items[i]
      if (!item.type.startsWith("image/")) continue

      event.preventDefault()
      const file = item.getAsFile()
      if (!file) continue

      if (file.size > MAX_IMAGE_SIZE) {
        window.alert(t("chat.imageTooBig"))
        return
      }

      const reader = new FileReader()
      reader.onload = (readerEvent) => {
        const result = readerEvent.target?.result as string
        const base64Data = result.split(",")[1]
        setSelectedImage(base64Data)
        setImagePreview(result)
      }
      reader.readAsDataURL(file)
      break
    }
  }

  const handleCopy = (content: string, index: number) => {
    navigator.clipboard.writeText(content)
    setCopiedIndex(index)
    window.setTimeout(() => setCopiedIndex(null), 1500)
  }

  const renderMarkdown = (content: string) => (
    <Markdown className="prose prose-slate max-w-none text-[15px] leading-7 dark:prose-invert" components={markdownComponents}>
      {content}
    </Markdown>
  )

  return (
    <>
      <div className="flex h-full min-h-0 bg-background">
        <div className="flex min-w-0 flex-1 flex-col">
          <ScrollArea className="min-h-0 flex-1">
            <motion.div
              layout
              transition={SOFT_SPRING}
              className={cn(
                "mx-auto flex w-full flex-col px-6",
                showWelcome
                  ? "max-w-[840px] items-center justify-center pb-20 pt-14"
                  : "max-w-[840px] gap-6 py-8"
              )}
            >
              <AnimatePresence initial={false}>
                {showWelcome && (
                  <motion.div
                    key="chat-welcome"
                    layout
                    variants={STAGGER_PARENT}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                    className="w-full max-w-[680px] space-y-8 text-center"
                  >
                    <motion.div variants={motionListItem} className="space-y-3">
                      <p className="text-sm text-muted-foreground">Geo-Agent</p>
                      <h1 className="text-2xl font-semibold tracking-tight text-foreground">{t("chat.welcome")}</h1>
                    </motion.div>

                    <motion.div variants={STAGGER_PARENT} className="flex flex-wrap justify-center gap-2">
                      {visibleSuggestedQuestions.map((question) => (
                        <motion.button
                          key={question}
                          type="button"
                          variants={motionListItem}
                          whileHover={shouldReduceMotion ? undefined : { y: -2 }}
                          whileTap={shouldReduceMotion ? undefined : { scale: 0.985 }}
                          transition={SOFT_SPRING}
                          onClick={() => setInput(question)}
                          className="rounded-full border border-border/80 px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                        >
                          {question}
                        </motion.button>
                      ))}
                    </motion.div>
                  </motion.div>
                )}
              </AnimatePresence>

              <AnimatePresence initial={false} mode="popLayout">
                {messages.map((message, index) => (
                <motion.div
                  key={`${message.role}-${index}`}
                  layout="position"
                  variants={motionListItem}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  transition={SOFT_SPRING}
                >
                  {message.role === "assistant" ? (
                    <div className="space-y-3">
                      <div className="max-w-[700px] text-foreground">
                        {isLoading && index === messages.length - 1 ? (
                          <StreamingMessage
                            content={streamingContent}
                            isStreaming={isLoading}
                            className="leading-7"
                          />
                        ) : (
                          renderMarkdown(message.content)
                        )}
                      </div>

                      {!isLoading && (
                        <motion.div layout="position" transition={SOFT_SPRING} className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => handleCopy(message.content, index)}
                            className={cn(
                              "flex h-[34px] w-[34px] items-center justify-center rounded-full border transition-colors",
                              copiedIndex === index
                                ? "border-[#b7c8fe] bg-[#edf3fe] text-primary"
                                : "border-border/80 text-muted-foreground hover:bg-secondary hover:text-foreground"
                            )}
                            title={t("chat.copy")}
                          >
                            {copiedIndex === index ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              const previousUserMessage = messages[index - 1]
                              if (previousUserMessage?.role === "user") {
                                setInput(previousUserMessage.content)
                              }
                            }}
                            className="flex h-[34px] w-[34px] items-center justify-center rounded-full border border-border/80 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                            title={t("chat.regenerate")}
                          >
                            <RotateCcw className="h-4 w-4" />
                          </button>
                          {sources.length > 0 && index === messages.length - 1 && (
                            <button
                              type="button"
                              onClick={() => setIsSourcesDialogOpen(true)}
                              className="inline-flex items-center gap-2 rounded-full border border-border/80 px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                            >
                              <BookOpen className="h-4 w-4" />
                              {t("chat.sources")}
                            </button>
                          )}
                        </motion.div>
                      )}

                      {!isLoading && index === messages.length - 1 && followUpQuestions.length > 0 && (
                        <motion.div
                          layout="position"
                          variants={STAGGER_PARENT}
                          initial="initial"
                          animate="animate"
                          className="space-y-2"
                        >
                          {followUpQuestions.map((question) => (
                            <motion.button
                              key={question}
                              type="button"
                              variants={motionListItem}
                              whileHover={shouldReduceMotion ? undefined : { x: 4 }}
                              whileTap={shouldReduceMotion ? undefined : { scale: 0.995 }}
                              transition={SOFT_SPRING}
                              onClick={() => handleFollowUpClick(question)}
                              className="flex w-full items-center gap-2 rounded-[20px] border border-border/80 px-4 py-3 text-left text-sm transition-colors hover:bg-secondary"
                            >
                              <span className="flex-1">{question}</span>
                              <ArrowRight className="h-4 w-4 text-muted-foreground" />
                            </motion.button>
                          ))}
                        </motion.div>
                      )}
                    </div>
                  ) : (
                    <div className="flex flex-col items-end gap-2">
                      <div className="max-w-[460px] rounded-[24px] border border-[#dbe5ff] bg-[#f4f7ff] px-4 py-3 text-sm leading-6 text-foreground dark:border-[#33436f] dark:bg-[#1a2237]">
                        {message.metadata?.image && (
                          <img
                            src={message.metadata.image}
                            alt={t("chat.userImageAlt")}
                            className="mb-3 max-h-64 rounded-2xl border border-border/70"
                          />
                        )}
                        <p className="whitespace-pre-wrap break-words">{message.content}</p>
                      </div>
                    </div>
                  )}
                </motion.div>
              ))}
              </AnimatePresence>

              <AnimatePresence initial={false}>
                {isLoading && !streamingContent && (
                  <motion.div
                    key="chat-status"
                    variants={motionListItem}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                    transition={SOFT_SPRING}
                  >
                    <ThinkingWave text={statusMessage || t("chat.thinking")} />
                  </motion.div>
                )}
              </AnimatePresence>

              <div ref={scrollRef} />
            </motion.div>
          </ScrollArea>

          <div className={cn("px-4 pb-6", showWelcome ? "pt-4" : "pt-3")}>
            <form onSubmit={handleSubmit} className="mx-auto w-full max-w-[840px]">
              <motion.div layout transition={SOFT_SPRING} className="shadow-ds-shell rounded-[28px] border border-border/80 bg-white p-2 dark:bg-card">
                <AnimatePresence>
                  {imagePreview && (
                    <motion.div
                      layout
                      variants={collapseMotion}
                      initial="initial"
                      animate="animate"
                      exit="exit"
                      transition={SOFT_SPRING}
                      className="px-2 pt-2"
                    >
                      <div className="relative inline-flex overflow-hidden rounded-[20px] border border-border/80">
                        <img src={imagePreview} alt={t("chat.previewAlt")} className="max-h-32 rounded-[20px]" />
                        <button
                          type="button"
                          onClick={handleRemoveImage}
                          className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-full bg-black/55 text-white"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <textarea
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={handleKeyDown}
                  onPaste={handlePaste}
                  placeholder={selectedImage ? t("chat.placeholderImage") : t("chat.placeholder")}
                  rows={3}
                  className="min-h-[92px] w-full resize-none border-none bg-transparent px-3 pt-3 text-base leading-6 text-foreground outline-none placeholder:text-muted-foreground"
                />

                <div className="flex flex-col gap-3 border-t border-border/70 px-2 pb-2 pt-3 md:flex-row md:items-center md:justify-between">
                  <div className="flex flex-wrap gap-2">
                    {(Object.entries(MODE_CONFIG) as Array<[ChatMode, (typeof MODE_CONFIG)["chat"]]>)?.map(([key, config]) => {
                      const Icon = config.icon
                      const isActive = mode === key
                      return (
                        <motion.button
                          key={key}
                          type="button"
                          whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
                          transition={SOFT_SPRING}
                          onClick={() => setMode(key)}
                          className={cn(
                            "relative inline-flex items-center gap-2 overflow-hidden rounded-full border px-3 py-1.5 text-sm transition-colors",
                            isActive ? "border-[#b7c8fe] text-primary" : "border-border/80 text-foreground hover:bg-secondary"
                          )}
                        >
                          {isActive && (
                            <motion.span
                              layoutId="chat-mode-active"
                              transition={SOFT_SPRING}
                              className="absolute inset-0 rounded-full bg-[#edf3fe] dark:bg-[#1f2942]"
                            />
                          )}
                          <span className="relative flex items-center gap-2">
                            <Icon className="h-4 w-4" />
                            {t(config.labelKey)}
                          </span>
                        </motion.button>
                      )
                    })}
                    <motion.button
                      type="button"
                      whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
                      transition={SOFT_SPRING}
                      onClick={() => setWebSearchEnabled((value) => !value)}
                      className={cn(
                        "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors",
                        webSearchEnabled
                          ? "border-[#b7c8fe] bg-[#edf3fe] text-primary"
                          : "border-border/80 text-foreground hover:bg-secondary"
                      )}
                    >
                      <Globe className="h-4 w-4" />
                      {t("chat.webSearch")}
                    </motion.button>
                    {mode === "rag" && (
                      <button
                        type="button"
                        onClick={() => setIsRagSettingsOpen(true)}
                        className="inline-flex items-center gap-2 rounded-full border border-border/80 px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-secondary"
                      >
                        <Settings2 className="h-4 w-4" />
                        {t("chat.settingsBtn")}
                      </button>
                    )}
                    {sources.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setIsSourcesDialogOpen(true)}
                        className="inline-flex items-center gap-2 rounded-full border border-border/80 px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-secondary"
                      >
                        <BookOpen className="h-4 w-4" />
                        {sources.length > 0 ? t("chat.sourceCount", { count: sources.length }) : t("chat.sources")}
                      </button>
                    )}
                  </div>

                  <div className="flex items-center justify-between gap-3 md:justify-end">
                    <div className="min-h-[20px] text-xs text-muted-foreground">
                      {statusMessage || (selectedImage ? t("chat.imageAttached") : "")}
                    </div>
                    <button
                      type="submit"
                      disabled={isLoading || (!input.trim() && !selectedImage)}
                      className="flex h-[34px] w-[34px] items-center justify-center rounded-full bg-primary text-primary-foreground transition-colors hover:bg-primary/95 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <Send className="h-4 w-4" />
                    </button>
                    </div>
                  </div>
              </motion.div>
            </form>
          </div>
        </div>
      </div>

      <Dialog open={isRagSettingsOpen} onOpenChange={setIsRagSettingsOpen}>
        <DialogContent className="max-w-[520px] gap-0 overflow-hidden p-0">
          <div className="border-b border-border/70 px-6 py-5">
            <DialogHeader className="text-left">
              <DialogTitle>{t("chat.ragSettings")}</DialogTitle>
              <DialogDescription>{t("chat.ragSettingsDesc")}</DialogDescription>
            </DialogHeader>
          </div>
          <div className="space-y-5 px-6 py-5">
            <div>
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{t("chat.topK")}</span>
                <span className="text-foreground">{topK} {t("chat.topKUnit")}</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={topK}
                onChange={(event) => setTopK(Number.parseInt(event.target.value, 10))}
                className="w-full accent-primary"
              />
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{t("chat.minRelevance")}</span>
                <span className="text-foreground">{Math.round(minRelevanceScore * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={minRelevanceScore}
                onChange={(event) => setMinRelevanceScore(Number.parseFloat(event.target.value))}
                className="w-full accent-primary"
              />
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={isSourcesDialogOpen} onOpenChange={setIsSourcesDialogOpen}>
        <DialogContent className="max-w-[620px] gap-0 overflow-hidden p-0">
          <div className="border-b border-border/70 px-6 py-5">
            <DialogHeader className="text-left">
              <DialogTitle>{t("chat.sources")}</DialogTitle>
              <DialogDescription>{t("chat.ragSettingsDesc")}</DialogDescription>
            </DialogHeader>
          </div>
          <ScrollArea className="max-h-[70vh]">
            <div className="divide-y divide-border/70">
              {sources.length === 0 ? (
                <div className="px-6 py-8 text-sm text-muted-foreground">{t("chat.noSources")}</div>
              ) : (
                sources.map((source, index) => (
                  <div key={`${source.source}-${index}`} className="px-6 py-4">
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedSourceIndex((previous) => (previous === index ? null : index))
                      }
                      className="flex w-full items-start gap-3 text-left"
                    >
                      <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-muted-foreground">
                        {source.type === "web" ? <Globe className="h-4 w-4" /> : <BookOpen className="h-4 w-4" />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="break-words text-sm font-medium text-foreground">{source.source}</p>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                          {source.source_type && <span>{source.source_type}</span>}
                          {source.relevance_score !== undefined && (
                            <span>{t("chat.relevanceScore", { score: Math.round(source.relevance_score * 100) })}</span>
                          )}
                        </div>
                      </div>
                      <motion.div
                        animate={{ rotate: expandedSourceIndex === index ? 90 : 0 }}
                        transition={SOFT_SPRING}
                      >
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      </motion.div>
                    </button>

                    <AnimatePresence initial={false}>
                      {expandedSourceIndex === index && (
                        <motion.div
                          variants={collapseMotion}
                          initial="initial"
                          animate="animate"
                          exit="exit"
                          transition={SOFT_SPRING}
                          className="overflow-hidden"
                        >
                          <div className="space-y-3 pl-11 pt-3 text-sm text-muted-foreground">
                            <p className="leading-6">{source.content}</p>
                            {source.images && source.images.length > 0 && (
                              <div className="flex flex-wrap gap-2">
                                {source.images!.map((img: any, i: number) => (
                                  <img
                                    key={i}
                                    src={img.base64}
                                    alt={t("chat.sourceImageAlt", { source: source.source, page: img.page || "?" })}
                                    className="max-h-48 max-w-full rounded-lg border border-border object-contain cursor-pointer hover:opacity-90 transition-opacity"
                                    onClick={() => window.open(img.base64, '_blank')}
                                  />
                                ))}
                              </div>
                            )}
                            {source.url && (
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 text-primary"
                              >
                                {t("chat.viewSource")}
                                <ArrowRight className="h-3.5 w-3.5" />
                              </a>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </>
  )
}
