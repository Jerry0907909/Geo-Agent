import React, { useState, useRef, useEffect, useCallback } from "react"
import { useParams, useNavigate, useSearchParams } from "react-router-dom"
import {
  agentService,
  chatService,
  conversationService,
  type AgentQueryResponse,
  type AgentRunState,
  type AgentRunStatus,
  type AgentStep,
  type AgentStepStatus,
  type ChatMessage,
  type Source,
  type ChatMode,
} from "@/services/api"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Loader2, Send, BookOpen, MessageCircle, Search, Sparkles, ChevronRight, ChevronDown, PanelRightClose, PanelRightOpen, Globe, Copy, Check, X, ThumbsUp, ThumbsDown, RotateCcw, ArrowRight, Square } from "lucide-react"
import Markdown from "react-markdown"
import { useChatStore } from "@/store/useChatStore"
import { motion, AnimatePresence, LayoutGroup } from "framer-motion"
import { cn } from "@/lib/utils"

const MODE_CONFIG = {
  chat: {
    label: '普通对话',
    icon: MessageCircle,
    description: '直接与AI对话',
    welcomeTitle: '常规问答',
    welcomeSubtitle: '适合快速提问与任务讨论',
  },
  rag: {
    label: '文献检索',
    icon: Search,
    description: '基于文献知识回答',
    welcomeTitle: '检索增强问答',
    welcomeSubtitle: '基于知识库与文献内容生成答案',
  },
  agent: {
    label: 'Agent',
    icon: Sparkles,
    description: '自动规划并逐步调用工具',
    welcomeTitle: '任务执行模式',
    welcomeSubtitle: '自动规划、工具调用、逐步完成复杂任务',
  },
}

// 图片大小限制 (5MB)
const MAX_IMAGE_SIZE = 5 * 1024 * 1024

// 消息反馈状态类型
type FeedbackType = 'like' | 'dislike' | null

type AgentTraceItem = {
  id: string
  phase: 'route' | 'plan' | 'step' | 'tool' | 'result' | 'synthesis' | 'error'
  title: string
  detail?: string
  tone?: 'neutral' | 'running' | 'success' | 'error'
}

const AGENT_STATUS_LABEL: Record<AgentRunStatus, string> = {
  queued: '等待执行',
  planning: '正在规划任务',
  running: '正在执行步骤',
  completed: '执行完成',
  failed: '执行失败',
  cancelled: '已取消',
}

const AGENT_STEP_STATUS_LABEL: Record<AgentStepStatus, string> = {
  pending: '待执行',
  running: '执行中',
  completed: '已完成',
  failed: '失败',
  skipped: '已跳过',
}

const RETRIEVAL_MODE_LABEL: Record<'local' | 'external' | 'hybrid', string> = {
  local: '本地知识库',
  external: '外部网页',
  hybrid: '混合检索',
}

const easeOutSoft = [0.22, 1, 0.36, 1] as const
const layoutSpring = { type: "spring", stiffness: 420, damping: 34, mass: 0.8 } as const

function createEmptyAgentRun(): AgentRunState {
  return {
    status: 'queued',
    steps: [],
    sources: [],
    error: null,
  }
}

function upsertAgentStep(steps: AgentStep[], nextStep: AgentStep): AgentStep[] {
  const index = steps.findIndex((step) => step.step_id === nextStep.step_id)
  if (index === -1) {
    return [...steps, nextStep]
  }
  const merged = { ...steps[index], ...nextStep }
  return steps.map((step, stepIndex) => (stepIndex === index ? merged : step))
}

function applyAgentRunResponse(run: AgentQueryResponse): AgentRunState {
  return {
    run_id: run.run_id,
    conversation_id: run.conversation_id,
    status: run.status as AgentRunStatus,
    plan_summary: run.plan_summary,
    steps: (run.steps || []).map(step => ({
      ...step,
      status: step.status as AgentStepStatus,
    })),
    final_answer: run.final_answer,
    sources: run.sources || [],
    error: run.error || null,
    execution_time: run.execution_time,
  }
}

export default function ChatPage() {
  const { conversationId } = useParams<{ conversationId?: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { currentConversationId, loadConversations, setCurrentConversationId } = useChatStore()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [sources, setSources] = useState<Source[]>([])
  const [mode, setMode] = useState<ChatMode>('chat')
  const scrollRef = useRef<HTMLDivElement>(null)
  const [isSourcesOpen, setIsSourcesOpen] = useState(true)
  const [expandedSourceIndex, setExpandedSourceIndex] = useState<number | null>(null)
  const [sourcePanelWidth, setSourcePanelWidth] = useState(560)
  const [isResizingSources, setIsResizingSources] = useState(false)
  const sourceResizeStartRef = useRef<{ startX: number; startWidth: number } | null>(null)
  
  // RAG 设置
  const [topK, setTopK] = useState(5)
  const [minRelevanceScore, setMinRelevanceScore] = useState(0.0)
  const [showRagSettings, setShowRagSettings] = useState(false)
  const [retrievalMode, setRetrievalMode] = useState<'local' | 'external' | 'hybrid'>('local')
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  
  // 图片上传状态
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  
  // 流式输出状态
  const [streamingContent, setStreamingContent] = useState("")
  const [statusMessage, setStatusMessage] = useState("")
  const [agentRun, setAgentRun] = useState<AgentRunState | null>(null)
  const [agentRouteInfo, setAgentRouteInfo] = useState<{ intent?: string; summary?: string; reason?: string } | null>(null)
  const [agentTrace, setAgentTrace] = useState<AgentTraceItem[]>([])
  const [isAgentTraceExpanded, setIsAgentTraceExpanded] = useState(true)
  const streamAbortRef = useRef<AbortController | null>(null)
  
  // 消息反馈状态 (messageIndex -> feedback)
  const [messageFeedback, setMessageFeedback] = useState<Record<number, FeedbackType>>({})
  
  // 推荐问题状态
  const [followUpQuestions, setFollowUpQuestions] = useState<string[]>([])
  const agentWebEnabled = retrievalMode !== 'local'
  const retrievalModeOptions: Array<{ value: 'local' | 'external' | 'hybrid', label: string, title: string }> = [
    { value: 'local', label: '本地', title: '仅使用本地知识库' },
    { value: 'external', label: '外部', title: '仅使用外部网页结果' },
    { value: 'hybrid', label: '混合', title: '融合本地知识库与外部网页结果' },
  ]
  
  // 处理消息反馈（点赞/倒赞）
  const handleFeedback = (messageIndex: number, type: FeedbackType) => {
    setMessageFeedback(prev => ({
      ...prev,
      [messageIndex]: prev[messageIndex] === type ? null : type
    }))
  }
  
  // 处理推荐问题点击
  const handleFollowUpClick = (question: string) => {
    setInput(question)
    setFollowUpQuestions([])
    // 自动提交
    setTimeout(() => {
      const form = document.querySelector('form')
      if (form) form.requestSubmit()
    }, 100)
  }
  
  // 生成推荐问题（基于最后的回答）
  const generateFollowUpQuestions = useCallback(async (answer: string, userQuestion: string) => {
    try {
      // 调用后端 API 生成推荐问题
      const response = await chatService.generateFollowUp(userQuestion, answer)
      if (response.questions && response.questions.length > 0) {
        setFollowUpQuestions(response.questions.slice(0, 3))
        return
      }
    } catch (err) {
      console.error('API 生成推荐问题失败，使用本地生成:', err)
    }
    
    // 本地备用生成逻辑
    const questions: string[] = []
    
    // 基于回答内容生成相关问题
    if (answer.includes('地质') || answer.includes('岩石')) {
      questions.push('这种地质现象的形成原因是什么？')
    }
    if (answer.includes('构造') || answer.includes('断层')) {
      questions.push('如何识别这种地质构造？')
    }
    if (answer.includes('矿物') || answer.includes('矿产')) {
      questions.push('这类矿物的主要分布区域在哪里？')
    }
    if (answer.includes('地震') || answer.includes('板块')) {
      questions.push('如何预测和防范相关地质灾害？')
    }
    if (answer.includes('水') || answer.includes('地下水')) {
      questions.push('地下水资源如何合理开发利用？')
    }
    
    // 通用问题
    if (questions.length < 3) {
      questions.push('能详细解释一下吗？')
      questions.push('有哪些实际应用案例？')
      questions.push('相关的研究进展如何？')
    }
    
    setFollowUpQuestions(questions.slice(0, 3))
  }, [])
  
  // 从 URL 参数恢复对话 ID
  useEffect(() => {
    if (conversationId) {
      const id = parseInt(conversationId)
      if (!isNaN(id)) {
        setCurrentConversationId(id)
      }
    } else {
      // URL 没有 conversationId 时，重置为新对话
      setCurrentConversationId(null)
    }
  }, [conversationId, setCurrentConversationId])

  // 是否显示开场白（新对话且没有消息）
  const showWelcome = !currentConversationId && messages.length === 0

  // Load messages when conversation changes
  useEffect(() => {
    // 使用 AbortController 来取消过期的请求
    let isCancelled = false
    
    const loadData = async () => {
      if (currentConversationId) {
        try {
          setIsLoading(true)
          const data = await conversationService.getMessages(currentConversationId)
          
          // 检查请求是否已被取消（用户切换了会话）
          if (isCancelled) return
          
          setMessages(data.messages)
          // Restore sources from last message if available
          const lastMsg = data.messages[data.messages.length - 1]
          if (lastMsg?.role === 'assistant' && lastMsg.metadata?.sources) {
            setSources(lastMsg.metadata.sources)
          } else {
            setSources([])
          }
        } catch (error) {
          if (!isCancelled) {
            console.error("Failed to load messages:", error)
          }
        } finally {
          if (!isCancelled) {
            setIsLoading(false)
          }
        }
      } else {
        // 新对话时清空消息，显示开场白界面
        setMessages([])
        setSources([])
        setIsLoading(false)
        setStreamingContent("")
        setStatusMessage("")
        setAgentRun(null)
        setAgentRouteInfo(null)
        setAgentTrace([])
        setIsAgentTraceExpanded(true)
      }
    }
    
    loadData()
    
    // 清理函数：当 effect 重新运行或组件卸载时取消请求
    return () => {
      isCancelled = true
    }
  }, [currentConversationId])

  // Scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages])

  useEffect(() => {
    if (!isResizingSources) return

    const onMouseMove = (event: MouseEvent) => {
      const start = sourceResizeStartRef.current
      if (!start) return
      const delta = start.startX - event.clientX
      const next = start.startWidth + delta
      const minWidth = 420
      const maxWidth = Math.min(900, Math.floor(window.innerWidth * 0.58))
      setSourcePanelWidth(Math.max(minWidth, Math.min(next, maxWidth)))
    }

    const onMouseUp = () => {
      setIsResizingSources(false)
      sourceResizeStartRef.current = null
    }

    document.body.style.cursor = "col-resize"
    window.addEventListener("mousemove", onMouseMove)
    window.addEventListener("mouseup", onMouseUp)
    return () => {
      document.body.style.cursor = ""
      window.removeEventListener("mousemove", onMouseMove)
      window.removeEventListener("mouseup", onMouseUp)
    }
  }, [isResizingSources])

  useEffect(() => {
    const runId = searchParams.get('agent_run_id')
    if (!runId || agentRun?.run_id === runId) {
      return
    }

    let isCancelled = false
    const restoreRun = async () => {
      try {
        const run = await agentService.getRun(runId)
        if (isCancelled) return
        setAgentRun(applyAgentRunResponse(run))
        if (run.sources?.length) {
          setSources(run.sources)
        }
      } catch (error) {
        if (!isCancelled) {
          console.error('Failed to restore agent run:', error)
        }
      }
    }

    restoreRun()
    return () => {
      isCancelled = true
    }
  }, [searchParams, agentRun?.run_id])

  // 移除已选图片
  const handleRemoveImage = useCallback(() => {
    setSelectedImage(null)
    setImagePreview(null)
  }, [])

  const handleCancelAgentRun = useCallback(async () => {
    const runId = agentRun?.run_id
    if (!runId) return

    try {
      await agentService.cancel(runId)
      setAgentRun(prev => prev ? { ...prev, status: 'cancelled', error: { code: 'RUN_CANCELLED', message: '任务已取消' } } : prev)
      setStatusMessage('任务已取消')
      setAgentTrace(prev => [...prev, {
        id: `trace-cancel-${Date.now()}`,
        phase: 'error',
        title: '任务已取消',
        detail: '用户主动终止了当前 Agent 执行。',
        tone: 'error',
      }])
    } catch (error) {
      console.error('Failed to cancel agent run:', error)
    } finally {
      streamAbortRef.current?.abort()
      streamAbortRef.current = null
      setIsLoading(false)
    }
  }, [agentRun?.run_id])

  const appendAgentTrace = useCallback((item: AgentTraceItem) => {
    setAgentTrace(prev => {
      const last = prev[prev.length - 1]
      if (last && last.phase === item.phase && last.title === item.title && last.detail === item.detail) {
        return prev
      }
      return [...prev, item]
    })
  }, [])

  const handleSubmit = useCallback(async (e?: React.FormEvent) => {
    e?.preventDefault()
    if ((!input.trim() && !selectedImage) || isLoading) return

    // 保存当前图片状态用于发送和显示
    const imageToSend = selectedImage
    const imagePreviewToShow = imagePreview
    
    const userMsg: ChatMessage = { 
      role: "user", 
      content: input || "请分析这张图片",
      metadata: imagePreviewToShow ? { image: imagePreviewToShow } : undefined
    }
    setMessages(prev => [...prev, userMsg])
    
    setInput("")
    setSelectedImage(null)
    setImagePreview(null)
    setIsLoading(true)
    setSources([])
    setStreamingContent("")
    setStatusMessage("")
    setAgentRun(mode === 'agent' ? createEmptyAgentRun() : null)
    setAgentRouteInfo(null)
    setAgentTrace([])
    setIsAgentTraceExpanded(true)

    try {
      let newConversationId: number | null = null
      let fullContent = ""
      let hasAddedPlaceholder = false
      const abortController = new AbortController()
      streamAbortRef.current = abortController
      
      // 缓冲区机制：先积累一定量的内容再开始显示
      let buffer = ""
      let displayedContent = ""
      let isBuffering = true
      const BUFFER_THRESHOLD = 50  // 积累50个字符后开始显示
      const CHAR_DELAY = 15  // 每个字符显示间隔（毫秒）
      let outputTimer: ReturnType<typeof setInterval> | null = null
      
      // 平滑输出函数
      const startSmoothOutput = () => {
        if (outputTimer) return
        
        outputTimer = setInterval(() => {
          if (displayedContent.length < buffer.length) {
            // 每次输出1-3个字符，模拟打字效果
            const charsToAdd = Math.min(
              Math.ceil(Math.random() * 2) + 1,
              buffer.length - displayedContent.length
            )
            displayedContent = buffer.slice(0, displayedContent.length + charsToAdd)
            setStreamingContent(displayedContent)
          }
        }, CHAR_DELAY)
      }
      
      // 清理定时器
      const stopSmoothOutput = () => {
        if (outputTimer) {
          clearInterval(outputTimer)
          outputTimer = null
        }
      }

      const stream = mode === 'agent'
        ? agentService.stream(
            {
              task: userMsg.content,
              conversation_id: currentConversationId,
              top_k: topK,
              allow_web_search: agentWebEnabled,
              return_steps: true,
              retrieval_mode: retrievalMode,
            },
            undefined,
            abortController.signal
          )
        : chatService.stream({
            message: userMsg.content,
            conversation_id: currentConversationId,
            mode: mode,
            top_k: topK,
            min_relevance_score: minRelevanceScore,
            web_search: retrievalMode !== 'local',
            retrieval_mode: retrievalMode,
            image_base64: imageToSend,
          })

      for await (const event of stream) {
        switch (event.type) {
          case 'info':
            if (event.conversation_id && !currentConversationId) {
              newConversationId = event.conversation_id
            }
            if (mode === 'agent') {
              const nextRunId = event.run_id || agentRun?.run_id
              if (nextRunId) {
                const params = new URLSearchParams(searchParams)
                params.set('agent_run_id', nextRunId)
                setSearchParams(params, { replace: true })
              }
              setAgentRun(prev => ({
                ...(prev || createEmptyAgentRun()),
                run_id: nextRunId,
                conversation_id: event.conversation_id || prev?.conversation_id,
                status: (event.status as AgentRunStatus) || prev?.status || 'queued',
                error: (event.status as AgentRunStatus) === 'cancelled'
                  ? { code: 'RUN_CANCELLED', message: '任务已取消' }
                  : prev?.error || null,
              }))
              setStatusMessage(AGENT_STATUS_LABEL[(event.status as AgentRunStatus) || 'queued'])
            }
            break
          
          case 'status':
            setStatusMessage(event.message || '')
            break

          case 'route':
            if (mode === 'agent') {
              setAgentRouteInfo({
                intent: event.intent,
                summary: event.summary,
                reason: event.reason,
              })
              setStatusMessage(event.summary || event.reason || '正在分析任务...')
              appendAgentTrace({
                id: `trace-route-${Date.now()}`,
                phase: 'route',
                title: event.summary || '正在判断任务路径',
                detail: event.reason,
                tone: 'running',
              })
            }
            break
          
          case 'content':
            if (mode === 'agent') {
              if (!fullContent) {
                appendAgentTrace({
                  id: `trace-synthesis-${Date.now()}`,
                  phase: 'synthesis',
                  title: '开始整理最终回答',
                  detail: 'Agent 正在把已获取的证据与观察结果汇总成简洁回答。',
                  tone: 'running',
                })
              }
              if (!hasAddedPlaceholder) {
                setMessages(prev => [...prev, { role: "assistant", content: "" }])
                hasAddedPlaceholder = true
              }
              fullContent += event.content || ''
              setStreamingContent(fullContent)
              setStatusMessage('正在生成回答...')
              setAgentRun(prev => ({
                ...(prev || createEmptyAgentRun()),
                run_id: event.run_id || prev?.run_id,
                conversation_id: event.conversation_id || prev?.conversation_id,
                status: prev?.status || 'running',
                final_answer: fullContent,
                sources: prev?.sources || [],
                error: prev?.error || null,
              }))
              break
            }
            if (!hasAddedPlaceholder) {
              setMessages(prev => [...prev, { role: "assistant", content: "" }])
              hasAddedPlaceholder = true
            }

            buffer += event.content || ''
            fullContent = buffer

            if (isBuffering && buffer.length >= BUFFER_THRESHOLD) {
              isBuffering = false
              setStatusMessage('')
              startSmoothOutput()
            }
            break
          
          case 'sources':
            if (event.sources) {
              setSources(event.sources)
              if (mode === 'agent') {
                setAgentRun(prev => prev ? { ...prev, sources: event.sources || prev.sources } : prev)
              }
            }
            break

          case 'plan':
            appendAgentTrace({
              id: `trace-plan-${Date.now()}`,
              phase: 'plan',
              title: event.summary || '已生成执行计划',
              detail: event.steps?.length ? `规划了 ${event.steps.length} 个执行步骤。` : '已生成结构化计划。',
              tone: 'neutral',
            })
            setAgentRun(prev => ({
              ...(prev || createEmptyAgentRun()),
              run_id: event.run_id || prev?.run_id,
              conversation_id: event.conversation_id || prev?.conversation_id,
              status: 'planning',
              plan_summary: event.summary || prev?.plan_summary,
              steps: (event.steps || []).map((step: AgentStep) => ({
                ...step,
                status: (step.status || 'pending') as AgentStepStatus,
              })),
              sources: prev?.sources || [],
              error: null,
            }))
            break

          case 'thought':
            appendAgentTrace({
              id: `trace-thought-${event.step_id || Date.now()}`,
              phase: 'plan',
              title: event.summary || '正在判断下一步',
              detail: event.tool_name ? `候选动作：${event.tool_name}` : 'Agent 正在决定下一步动作。',
              tone: 'neutral',
            })
            setStatusMessage(event.summary || '正在判断下一步动作')
            break

          case 'step_start':
            appendAgentTrace({
              id: `trace-step-${event.step_id || Date.now()}`,
              phase: 'step',
              title: event.title || event.step_id || '开始执行步骤',
              detail: event.goal,
              tone: 'running',
            })
            setAgentRun(prev => {
              const base = prev || createEmptyAgentRun()
              return {
                ...base,
                status: 'running',
                steps: upsertAgentStep(base.steps, {
                  step_id: event.step_id || '',
                  title: event.title || '未命名步骤',
                  goal: event.goal,
                  tool_name: event.tool_name || 'unknown_tool',
                  status: 'running',
                }),
              }
            })
            setStatusMessage(`正在执行：${event.title || event.step_id || '步骤'}`)
            break

          case 'tool_call':
            appendAgentTrace({
              id: `trace-tool-${event.step_id || Date.now()}`,
              phase: 'tool',
              title: `调用工具 ${event.tool_name || 'unknown_tool'}`,
              detail: '正在等待工具返回结果。',
              tone: 'running',
            })
            setAgentRun(prev => {
              if (!prev) return prev
              return {
                ...prev,
                steps: prev.steps.map(step => (
                  step.step_id === event.step_id
                    ? { ...step, tool_input: event.input || event.tool_input || step.tool_input, status: 'running' }
                    : step
                )),
              }
            })
            setStatusMessage(`调用工具：${event.tool_name || 'unknown_tool'}`)
            break

          case 'tool_result':
            appendAgentTrace({
              id: `trace-result-${event.step_id || Date.now()}`,
              phase: 'result',
              title: `${event.tool_name || '工具'}${event.error ? ' 执行失败' : ' 已返回结果'}`,
              detail: event.observation,
              tone: event.error ? 'error' : 'success',
            })
            setAgentRun(prev => {
              const base = prev || createEmptyAgentRun()
              return {
                ...base,
                status: event.error ? 'running' : base.status,
                steps: upsertAgentStep(base.steps, {
                  step_id: event.step_id || '',
                  title: base.steps.find(step => step.step_id === event.step_id)?.title || event.step_id || '步骤',
                  tool_name: event.tool_name || base.steps.find(step => step.step_id === event.step_id)?.tool_name || 'unknown_tool',
                  status: ((event.status || (event.error ? 'failed' : 'completed')) as AgentStepStatus),
                  observation: event.observation,
                  latency_ms: event.latency_ms,
                  sources: event.sources,
                }),
              }
            })
            break

          case 'replan':
            setAgentRun(prev => {
              const base = prev || createEmptyAgentRun()
              const appended = (event.steps || []).reduce((acc: AgentStep[], step: AgentStep) => (
                upsertAgentStep(acc, { ...step, status: (step.status || 'pending') as AgentStepStatus })
              ), base.steps)
              return {
                ...base,
                plan_summary: event.summary || base.plan_summary,
                steps: appended,
              }
            })
            setStatusMessage(event.message || '正在调整执行计划')
            break

          case 'final':
            fullContent = event.final_answer || fullContent
            setAgentRun(prev => ({
              ...(prev || createEmptyAgentRun()),
              run_id: event.run_id || prev?.run_id,
              conversation_id: event.conversation_id || prev?.conversation_id,
              status: 'completed',
              final_answer: event.final_answer,
              sources: event.sources || prev?.sources || [],
              execution_time: event.execution_time,
              error: null,
            }))
            if (event.sources) {
              setSources(event.sources)
            }
            if (!hasAddedPlaceholder && fullContent) {
              setMessages(prev => [...prev, { role: "assistant", content: "" }])
              hasAddedPlaceholder = true
            }
            if (mode === 'agent' && fullContent) {
              setStreamingContent(fullContent)
            }
            break
          
          case 'done':
            setStatusMessage('')
            stopSmoothOutput()
            if (mode === 'agent') {
              setIsAgentTraceExpanded(false)
            }
            
            // 如果还在缓冲阶段（内容很短），直接显示全部
            if (isBuffering && buffer.length > 0) {
              setStreamingContent(buffer)
            }
            
            // 等待显示追上缓冲区
            if (mode !== 'agent') {
              while (displayedContent.length < buffer.length) {
                await new Promise(resolve => setTimeout(resolve, 10))
                const charsToAdd = Math.min(5, buffer.length - displayedContent.length)
                displayedContent = buffer.slice(0, displayedContent.length + charsToAdd)
                setStreamingContent(displayedContent)
              }
            }
            
            if (newConversationId) {
              setCurrentConversationId(newConversationId)
              loadConversations()
              navigate(`/chat/${newConversationId}`, { replace: true })
            }
            
            // 固化最终内容到消息列表
            if (fullContent) {
              setMessages(prev => {
                const updated = [...prev]
                const lastIndex = updated.length - 1
                if (lastIndex >= 0 && updated[lastIndex].role === "assistant") {
                  updated[lastIndex] = {
                    ...updated[lastIndex],
                    content: fullContent,
                  }
                } else if (mode === 'agent') {
                  updated.push({ role: "assistant", content: fullContent })
                }
                return updated
              })
              
              // 生成推荐问题
              generateFollowUpQuestions(fullContent, userMsg.content)
            }
            break
          
          case 'error':
            stopSmoothOutput()
            if (mode === 'agent') {
              appendAgentTrace({
                id: `trace-error-${Date.now()}`,
                phase: 'error',
                title: 'Agent 执行失败',
                detail: event.message || event.error?.message || '执行过程中出现错误。',
                tone: 'error',
              })
            }
            if (mode === 'agent') {
              setAgentRun(prev => ({
                ...(prev || createEmptyAgentRun()),
                run_id: event.run_id || prev?.run_id,
                conversation_id: event.conversation_id || prev?.conversation_id,
                status: 'failed',
                error: {
                  code: event.code || event.error?.code || 'AGENT_ERROR',
                  message: event.message || event.error?.message || 'Agent 执行失败',
                },
              }))
            }
            throw new Error(event.message)
        }
      }
    } catch (error) {
      console.error("Chat failed:", error)
      if ((error as Error).name === 'AbortError') {
        return
      }
      if (mode !== 'agent') {
        setMessages(prev => [...prev, {
          role: "assistant",
          content: "抱歉，我遇到了一些问题，请稍后再试。"
        }])
      }
    } finally {
      streamAbortRef.current = null
      setIsLoading(false)
      setStreamingContent("")
      if (mode !== 'agent') {
        setStatusMessage("")
      }
    }
  }, [input, isLoading, currentConversationId, mode, loadConversations, setCurrentConversationId, selectedImage, imagePreview, topK, minRelevanceScore, retrievalMode, navigate, generateFollowUpQuestions, agentRun?.run_id, setSearchParams, appendAgentTrace])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }
  
  // 处理粘贴事件（支持 Ctrl+V 粘贴图片）
  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items
    if (!items) return
    
    for (let i = 0; i < items.length; i++) {
      const item = items[i]
      if (item.type.startsWith('image/')) {
        e.preventDefault()
        const file = item.getAsFile()
        if (!file) continue
        
        // 检查文件大小
        if (file.size > MAX_IMAGE_SIZE) {
          alert('图片大小不能超过5MB')
          return
        }
        
        // 读取文件并转换为base64
        const reader = new FileReader()
        reader.onload = (event) => {
          const result = event.target?.result as string
          const base64Data = result.split(',')[1]
          setSelectedImage(base64Data)
          setImagePreview(result)
        }
        reader.readAsDataURL(file)
        break
      }
    }
  }, [])
  
  const handleCopy = (content: string, index: number) => {
    navigator.clipboard.writeText(content)
    setCopiedIndex(index)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  const handleSourceResizeStart = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!isSourcesOpen) return
    sourceResizeStartRef.current = { startX: event.clientX, startWidth: sourcePanelWidth }
    setIsResizingSources(true)
    event.preventDefault()
  }

  const currentAgentStep = agentRun?.steps.find((step) => step.status === 'running')
  const latestAgentStep = agentRun?.steps[agentRun.steps.length - 1]
  const synthesisPreview = mode === 'agent' ? (streamingContent || agentRun?.final_answer || '') : ''
  const completedAgentSteps = agentRun?.steps.filter((step) => step.status === 'completed').length || 0
  const failedAgentSteps = agentRun?.steps.filter((step) => step.status === 'failed').length || 0
  const shownAgentSteps = agentRun?.steps.slice(-5) || []
  const documentSources = sources.filter((source) => source.type !== 'web')
  const webSources = sources.filter((source) => source.type === 'web')
  const isAgentActive = agentRun?.status === 'queued' || agentRun?.status === 'planning' || agentRun?.status === 'running'
  const isAgentWorkspace = mode === 'agent' && !showWelcome
  const contentMaxWidth = "max-w-[920px] xl:max-w-[980px] 2xl:max-w-[980px]"
  const composeMaxWidth = "max-w-[920px]"
  const proseWidth = "max-w-[820px]"
  const currentModeConfig = MODE_CONFIG[mode]
  const showRetrievalControls = mode === 'rag'
  const markdownComponents = {
    p: ({ children }: any) => <p className="mb-3 text-[14px] leading-7 last:mb-0">{children}</p>,
    ul: ({ children }: any) => <ul className="mb-3 list-disc space-y-1 pl-5 text-[14px]">{children}</ul>,
    ol: ({ children }: any) => <ol className="mb-3 list-decimal space-y-1 pl-5 text-[14px]">{children}</ol>,
    li: ({ children }: any) => <li className="leading-7">{children}</li>,
    code: ({ inline, children, ...props }: any) => (
      inline ? (
        <code className="rounded-md bg-muted px-1.5 py-0.5 text-[13px] text-foreground" {...props}>
          {children}
        </code>
      ) : (
        <code className="mb-3 block overflow-x-auto rounded-2xl border border-border bg-card p-4 text-[13px] text-foreground shadow-sm" {...props}>
          {children}
        </code>
      )
    ),
  }

  return (
    <div className="flex h-full w-full overflow-hidden bg-transparent">
      <div className="flex h-full w-full overflow-hidden">
        <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden bg-transparent">
          <ScrollArea className="flex-1">
            <div className={cn("mx-auto flex w-full flex-col gap-8 px-5 pb-28 pt-5 md:px-8", isAgentWorkspace ? "max-w-[980px] xl:max-w-[1060px]" : contentMaxWidth)}>
                {showWelcome && (
                  <LayoutGroup>
                  <motion.div layout transition={layoutSpring} className={cn("mx-auto flex min-h-[52vh] w-full flex-col items-center justify-center gap-4 py-8 animate-in fade-in duration-300", composeMaxWidth)}>
                    <div className="max-w-[840px] text-center">
                      <AnimatePresence mode="wait" initial={false}>
                        <motion.h1
                          key={mode}
                          initial={{ opacity: 0, y: 8, filter: "blur(2px)" }}
                          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                          exit={{ opacity: 0, y: -6, filter: "blur(2px)" }}
                          transition={{ duration: 0.22, ease: easeOutSoft }}
                          className="inline-flex items-center gap-3 text-[clamp(1.95rem,2.6vw,2.85rem)] font-semibold leading-[1.12] tracking-[-0.02em] text-foreground md:whitespace-nowrap"
                        >
                          <currentModeConfig.icon className="h-7 w-7 text-primary" />
                          <span>使用{currentModeConfig.label}开始对话</span>
                        </motion.h1>
                      </AnimatePresence>
                    </div>

                    <div className="surface-subtle inline-flex rounded-full p-1">
                      {(Object.entries(MODE_CONFIG) as [ChatMode, typeof MODE_CONFIG.chat][]).map(([key, config]) => {
                        const Icon = config.icon
                        return (
                          <button
                            key={key}
                            onClick={() => setMode(key)}
                            className={cn("mode-segment rounded-full px-5", mode === key && "mode-segment-active")}
                            title={config.description}
                          >
                            <Icon className="h-3.5 w-3.5" />
                            <span>{config.label}</span>
                          </button>
                        )
                      })}
                    </div>

                    <motion.div layout transition={layoutSpring} className="floating-compose w-full max-w-[860px] overflow-hidden rounded-[30px] px-4 py-3 dark:bg-[#182233]">
                      <AnimatePresence>
                        {imagePreview && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            className="px-1 pb-2"
                          >
                            <div className="relative inline-block">
                              <img
                                src={imagePreview}
                                alt="预览"
                                className="max-h-28 rounded-xl border border-border/70"
                              />
                              <button
                                onClick={handleRemoveImage}
                                className="absolute -right-2 -top-2 rounded-full bg-red-500 p-1 text-white transition-colors hover:bg-red-600"
                              >
                                <X className="h-3 w-3" />
                              </button>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>

                      <div className="flex items-end gap-3 px-1 py-1">
                        <textarea
                          value={input}
                          onChange={(e) => setInput(e.target.value)}
                          onKeyDown={handleKeyDown}
                          onPaste={handlePaste}
                          placeholder={selectedImage ? "描述你想了解的内容..." : "给 Geo-Agent 发送消息"}
                          rows={1}
                          className="min-h-[56px] flex-1 resize-none bg-transparent border-none px-1 pt-1 text-[16px] leading-7 text-foreground placeholder:text-muted-foreground/72 focus:outline-none"
                          style={{ maxHeight: "180px" }}
                        />
                        <motion.button
                          onClick={() => handleSubmit()}
                          disabled={isLoading || (!input.trim() && !selectedImage)}
                          whileHover={{ scale: isLoading || (!input.trim() && !selectedImage) ? 1 : 1.03 }}
                          whileTap={{ scale: isLoading || (!input.trim() && !selectedImage) ? 1 : 0.97 }}
                          className="mb-1 flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-primary/55 text-primary-foreground transition-all duration-200 hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-45"
                        >
                          <Send className="h-4 w-4" />
                        </motion.button>
                      </div>

                      <AnimatePresence initial={false}>
                        {showRetrievalControls && (
                          <motion.div
                            key="welcome-retrieval-controls"
                            initial={{ opacity: 0, height: 0, y: -6 }}
                            animate={{ opacity: 1, height: "auto", y: 0 }}
                            exit={{ opacity: 0, height: 0, y: -6 }}
                            transition={{ duration: 0.24, ease: easeOutSoft }}
                            className="overflow-hidden"
                          >
                            <div className="mt-2 flex min-h-[38px] items-center justify-between border-t soft-divider px-1.5 pt-2">
                              <div className="flex min-h-[30px] flex-wrap items-center gap-2">
                                <div className="surface-subtle inline-flex rounded-full p-1">
                                  {retrievalModeOptions.map((option) => (
                                    <button
                                      key={option.value}
                                      onClick={() => setRetrievalMode(option.value)}
                                      className={cn("mode-segment rounded-full px-3", retrievalMode === option.value && "mode-segment-active")}
                                      title={option.title}
                                    >
                                      <Globe className="h-3.5 w-3.5" />
                                      <span>{option.label}</span>
                                    </button>
                                  ))}
                                </div>
                                <button
                                  onClick={() => setShowRagSettings(!showRagSettings)}
                                  className={cn("deep-chip !rounded-full", showRagSettings && "deep-chip-active")}
                                  title="检索设置"
                                >
                                  <ChevronRight className={cn("h-3 w-3 transition-transform", showRagSettings && "rotate-90")} />
                                  <span>检索设置</span>
                                </button>
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  </motion.div>
                  </LayoutGroup>
                )}
                
                {messages.map((msg, i) => {
                  const isWelcomeMessage = i === 0 && msg.role === "assistant" && !currentConversationId && messages.length === 1
                  const isStreamingMessage = isLoading && i === messages.length - 1 && Boolean(streamingContent)

                  return (
                    <div
                      key={i}
                      className="group relative animate-in fade-in slide-in-from-bottom-2 duration-200"
                    >
                      {msg.role === "assistant" ? (
                        <div className="relative px-2 md:px-4">
                          <div className="mb-4 flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                              <Sparkles className="h-4 w-4" />
                            </div>
                            <div>
                              <p className="text-[15px] font-semibold text-foreground">Geo-Agent</p>
                            </div>
                          </div>

                          <div className={cn("assistant-content prose-refined prose prose-sm max-w-none", proseWidth, isAgentWorkspace && "max-w-[760px]")}>
                            {isStreamingMessage ? (
                              <div className="leading-8">
                                <Markdown
                                  className={cn("prose-refined prose leading-8", proseWidth, isAgentWorkspace && "max-w-[760px]")}
                                  components={markdownComponents}
                                >
                                  {streamingContent}
                                </Markdown>
                                <motion.span
                                  className="ml-1 inline-block h-5 w-0.5 bg-primary"
                                  animate={{ opacity: [1, 0] }}
                                  transition={{ duration: 0.8, repeat: Infinity }}
                                />
                              </div>
                            ) : (
                              <Markdown
                                className={cn("prose-refined prose leading-8", proseWidth, isAgentWorkspace && "max-w-[760px]")}
                                components={markdownComponents}
                              >
                                {msg.content}
                              </Markdown>
                            )}
                          </div>

                          {!isWelcomeMessage && !isLoading && (
                            <div className="mt-4 flex items-center gap-1.5 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                              <button
                                onClick={() => handleCopy(msg.content, i)}
                                className={cn(
                                  "rounded-xl p-2 transition-all duration-200",
                                  copiedIndex === i
                                    ? "bg-emerald-100 text-emerald-700"
                                    : "text-muted-foreground hover:bg-muted/70 hover:text-foreground"
                                )}
                                title="复制"
                              >
                                {copiedIndex === i ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                              </button>
                              <button
                                onClick={() => handleFeedback(i, "like")}
                                className={cn(
                                  "rounded-xl p-2 transition-all duration-200",
                                  messageFeedback[i] === "like"
                                    ? "bg-primary/10 text-primary"
                                    : "text-muted-foreground hover:bg-muted/70 hover:text-foreground"
                                )}
                                title="有帮助"
                              >
                                <ThumbsUp className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => handleFeedback(i, "dislike")}
                                className={cn(
                                  "rounded-xl p-2 transition-all duration-200",
                                  messageFeedback[i] === "dislike"
                                    ? "bg-destructive/10 text-destructive"
                                    : "text-muted-foreground hover:bg-muted/70 hover:text-foreground"
                                )}
                                title="没帮助"
                              >
                                <ThumbsDown className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => {
                                  const userMsgIndex = i - 1
                                  if (userMsgIndex >= 0 && messages[userMsgIndex]?.role === "user") {
                                    setInput(messages[userMsgIndex].content)
                                  }
                                }}
                                className="rounded-xl p-2 text-muted-foreground transition-all duration-200 hover:bg-muted/70 hover:text-foreground"
                                title="重新生成"
                              >
                                <RotateCcw className="h-4 w-4" />
                              </button>
                            </div>
                          )}

                          {!isLoading && i === messages.length - 1 && followUpQuestions.length > 0 && (
                            <div className="mt-7 flex flex-wrap gap-2.5">
                              {followUpQuestions.map((question, qIndex) => (
                                <button
                                  key={qIndex}
                                  onClick={() => handleFollowUpClick(question)}
                                  className="group inline-flex max-w-full items-center gap-2 rounded-full border border-black/5 bg-[#f7f9fc] px-4 py-2.5 text-left text-sm text-foreground transition-all duration-200 hover:border-primary/20 hover:bg-slate-100 dark:border-white/8 dark:bg-[#1a2335] dark:text-slate-100 dark:hover:bg-[#223049]"
                                >
                                  <span className="line-clamp-1">{question}</span>
                                  <ArrowRight className="h-4 w-4 text-muted-foreground opacity-60 transition-opacity group-hover:opacity-100" />
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="flex flex-col items-end">
                          <div className="inline-block max-w-[74%] rounded-[28px] border border-black/5 bg-[#f3f6fb] px-5 py-3.5 text-foreground dark:border-white/8 dark:bg-[#1c2739] dark:text-slate-100">
                            {msg.metadata?.image && (
                              <img
                                src={msg.metadata.image}
                                alt="用户上传的图片"
                                className="mb-3 max-h-64 max-w-full rounded-[20px] border border-black/5"
                              />
                            )}
                            <p className="whitespace-pre-wrap break-words text-[15px] leading-7">{msg.content}</p>
                          </div>
                          <div className="mt-2 flex items-center gap-2 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                            <button
                              onClick={() => handleCopy(msg.content, i)}
                              className="flex items-center gap-1 rounded-full px-2.5 py-1 text-xs text-muted-foreground transition-all duration-200 hover:bg-muted/70 hover:text-foreground"
                            >
                              {copiedIndex === i ? (
                                <>
                                  <Check className="h-3.5 w-3.5 text-green-600" />
                                  <span className="text-green-600">已复制</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="h-3.5 w-3.5" />
                                  <span>复制</span>
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
                {isAgentWorkspace && agentRun && isAgentActive && synthesisPreview && (
                  <div className="px-2 md:px-4">
                    <div className="mb-4 flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                        <Sparkles className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-[15px] font-semibold text-foreground">Geo-Agent</p>
                        <p className="text-[12px] text-muted-foreground">Agent 正在生成答案</p>
                      </div>
                    </div>
                    <div className="max-w-[760px]">
                      <Markdown className="prose-refined prose max-w-none leading-8">
                        {synthesisPreview}
                      </Markdown>
                      <motion.span
                        className="ml-1 mt-1 inline-block h-5 w-0.5 bg-primary"
                        animate={{ opacity: [1, 0] }}
                        transition={{ duration: 0.8, repeat: Infinity }}
                      />
                    </div>
                  </div>
                )}
                {isLoading && !streamingContent && mode !== 'agent' && (
                  <div className="surface-strong flex items-center gap-2 rounded-full px-3 py-2 text-sm animate-in fade-in duration-200">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    <span className="text-sm text-muted-foreground">
                      {statusMessage || '正在思考...'}
                    </span>
                  </div>
                )}
                <div ref={scrollRef} />
              </div>
            </ScrollArea>

            {!showWelcome && (
            <div className="bg-transparent px-3 pb-5 pt-3">
              <motion.div layout transition={layoutSpring} className={cn("mx-auto space-y-2.5", composeMaxWidth)}>
                <AnimatePresence initial={false}>
                  {mode === 'rag' && showRagSettings && (
                    <motion.div
                      initial={{ opacity: 0, height: 0, y: 8 }}
                      animate={{ opacity: 1, height: 'auto', y: 0 }}
                      exit={{ opacity: 0, height: 0, y: 8 }}
                      transition={{ duration: 0.24, ease: easeOutSoft }}
                      className="shell-panel overflow-hidden rounded-[24px] p-4 space-y-3"
                    >
                    <div className="mb-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">检索设置</div>
                    <div className="surface-subtle rounded-[18px] px-3 py-2.5 text-xs text-muted-foreground">
                      当前检索模式：<span className="font-medium text-foreground">
                        {RETRIEVAL_MODE_LABEL[retrievalMode]}
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <label className="text-muted-foreground">参考来源数量</label>
                        <span className="font-medium">{topK} 条</span>
                      </div>
                      <input type="range" min="1" max="10" step="1" value={topK} onChange={(e) => setTopK(parseInt(e.target.value))} className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary" />
                    </div>
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <label className="text-muted-foreground">最小相关度</label>
                        <span className="font-medium">{(minRelevanceScore * 100).toFixed(0)}%</span>
                      </div>
                      <input type="range" min="0" max="1" step="0.05" value={minRelevanceScore} onChange={(e) => setMinRelevanceScore(parseFloat(e.target.value))} className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary" />
                    </div>
                    </motion.div>
                  )}
                </AnimatePresence>
                
                <motion.div layout transition={layoutSpring} className="floating-compose overflow-hidden rounded-[28px] px-3 py-3 transition-colors duration-200 hover:border-primary/30 dark:bg-[#182233]">
                  <AnimatePresence>
                    {imagePreview && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="px-2 pb-3"
                      >
                        <div className="relative inline-block">
                          <img 
                            src={imagePreview} 
                            alt="预览" 
                            className="max-h-28 rounded-xl border border-border/70"
                          />
                          <button
                            onClick={handleRemoveImage}
                            className="absolute -right-2 -top-2 rounded-full bg-red-500 p-1 text-white shadow-md transition-colors hover:bg-red-600"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                  
                    <div className="flex items-end gap-3 px-2 py-1">
                      <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      onPaste={handlePaste}
                      placeholder={selectedImage ? "描述你想了解的内容..." : "给 Geo-Agent 发送消息"}
                      rows={1}
                        className="min-h-[56px] flex-1 resize-none bg-transparent border-none text-[15px] leading-7 text-foreground placeholder:text-muted-foreground/76 focus:outline-none"
                        style={{ maxHeight: '180px' }}
                      />
                    <motion.button
                      onClick={() => handleSubmit()}
                      disabled={isLoading || (!input.trim() && !selectedImage)}
                      whileHover={{ scale: isLoading || (!input.trim() && !selectedImage) ? 1 : 1.05 }}
                      whileTap={{ scale: isLoading || (!input.trim() && !selectedImage) ? 1 : 0.95 }}
                        className="mb-1 flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-all duration-200 hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        <Send className="h-4 w-4" />
                      </motion.button>
                    </div>

                  <AnimatePresence initial={false}>
                    {showRetrievalControls && (
                      <motion.div
                        key="dock-retrieval-controls"
                        initial={{ opacity: 0, height: 0, y: -6 }}
                        animate={{ opacity: 1, height: "auto", y: 0 }}
                        exit={{ opacity: 0, height: 0, y: -6 }}
                        transition={{ duration: 0.24, ease: easeOutSoft }}
                        className="overflow-hidden"
                      >
                        <div className="mt-2 flex min-h-[38px] items-center border-t soft-divider px-2 pt-2">
                          <div className="flex min-h-[30px] items-center gap-2 overflow-x-auto">
                            <div className="surface-subtle inline-flex rounded-full p-1">
                              {retrievalModeOptions.map((option) => (
                                <button
                                  key={option.value}
                                  onClick={() => setRetrievalMode(option.value)}
                                  className={cn("mode-segment rounded-full px-3", retrievalMode === option.value && "mode-segment-active")}
                                  title={option.title}
                                >
                                  <Globe className="h-3.5 w-3.5" />
                                  <span>{option.label}</span>
                                </button>
                              ))}
                            </div>
                            <button
                              onClick={() => setShowRagSettings(!showRagSettings)}
                              className={cn("deep-chip !rounded-full", showRagSettings && "deep-chip-active")}
                              title="检索设置"
                            >
                              <ChevronRight className={cn("h-3 w-3 transition-transform", showRagSettings && "rotate-90")} />
                              <span>检索设置</span>
                            </button>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              </motion.div>
            </div>
            )}
          </div>

          {(isAgentWorkspace || sources.length > 0) && (
            <motion.div 
              initial={{ width: isAgentWorkspace ? (isSourcesOpen ? 380 : 56) : 56 }}
              animate={{ width: isAgentWorkspace ? (isSourcesOpen ? 380 : 56) : isSourcesOpen ? sourcePanelWidth : 56 }}
              transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
              className="relative m-4 ml-0 hidden flex-col overflow-hidden rounded-[24px] shell-panel lg:flex"
            >
              {!isAgentWorkspace && isSourcesOpen && (
                <div
                  onMouseDown={handleSourceResizeStart}
                  className={cn(
                    "absolute left-0 top-0 z-20 h-full w-2 -translate-x-1/2 cursor-col-resize",
                    isResizingSources ? "bg-primary/15" : "bg-transparent hover:bg-primary/10"
                  )}
                  title="拖拽调整宽度"
                />
              )}
              <div className="surface-subtle flex items-center gap-2 border-b soft-divider px-4 py-3 font-medium">
                {isAgentWorkspace ? (
                  <>
                    <motion.button
                      onClick={() => setIsSourcesOpen(!isSourcesOpen)}
                      className="rounded-2xl p-1.5 transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                      title={isSourcesOpen ? '收起进度栏' : '展开进度栏'}
                      whileHover={{ scale: 1.08 }}
                      whileTap={{ scale: 0.96 }}
                    >
                      <motion.div
                        animate={{ rotate: isSourcesOpen ? 0 : 180 }}
                        transition={{ duration: 0.3 }}
                      >
                        {isSourcesOpen ? <PanelRightOpen className="h-4 w-4" /> : <PanelRightClose className="h-4 w-4" />}
                      </motion.div>
                    </motion.button>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-foreground">进度</span>
                    </div>
                    {isAgentActive && (
                      <button
                        onClick={handleCancelAgentRun}
                        className="ml-auto inline-flex items-center gap-1 rounded-full px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-black/5 hover:text-foreground dark:hover:bg-white/5"
                      >
                        <Square className="h-3 w-3" />
                        取消
                      </button>
                    )}
                  </>
                ) : (
                  <>
                    <motion.button
                      onClick={() => setIsSourcesOpen(!isSourcesOpen)}
                      className="rounded-2xl p-1.5 transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                      title={isSourcesOpen ? '收起参考来源' : '展开参考来源'}
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      <motion.div
                        animate={{ rotate: isSourcesOpen ? 0 : 180 }}
                        transition={{ duration: 0.3 }}
                      >
                        {isSourcesOpen ? <PanelRightOpen className="h-4 w-4" /> : <PanelRightClose className="h-4 w-4" />}
                      </motion.div>
                    </motion.button>
                    <AnimatePresence mode="wait">
                      {isSourcesOpen && (
                        <motion.div
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -10 }}
                          transition={{ duration: 0.2 }}
                          className="flex items-center gap-2"
                        >
                          <BookOpen className="h-3.5 w-3.5 text-primary" />
                          <span className="text-sm text-foreground">参考来源</span>
                          <span className="text-xs text-muted-foreground">({sources.length})</span>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </>
                )}
              </div>
              <AnimatePresence>
                {((isAgentWorkspace && isSourcesOpen) || (!isAgentWorkspace && isSourcesOpen)) && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="flex-1 overflow-hidden"
                  >
                    <ScrollArea className="h-full">
                      <motion.div className="space-y-5 px-4 py-4">
                        {isAgentWorkspace && (
                          <div className="space-y-5">
                            {agentRun ? (
                              <div className="surface-panel rounded-[22px] px-4 py-4 dark:bg-[#182233]">
                                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                                  {isAgentActive && <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />}
                                  <span>{AGENT_STATUS_LABEL[agentRun.status]}</span>
                                  <span>·</span>
                                  <span>{completedAgentSteps} 已完成</span>
                                  {failedAgentSteps > 0 && (
                                    <>
                                      <span>·</span>
                                      <span>{failedAgentSteps} 失败</span>
                                    </>
                                  )}
                                  {agentRun.execution_time && (
                                    <>
                                      <span>·</span>
                                      <span>{agentRun.execution_time.toFixed(2)}s</span>
                                    </>
                                  )}
                                </div>
                                <div className="mt-3 text-[15px] font-medium text-foreground">
                                  {currentAgentStep?.title || latestAgentStep?.title || agentRouteInfo?.summary || agentRun.plan_summary || '正在识别任务路径'}
                                </div>
                                <div className="mt-1.5 text-sm leading-6 text-muted-foreground">
                                  {currentAgentStep?.goal || latestAgentStep?.goal || agentRouteInfo?.reason || statusMessage || 'Agent 会按需决定下一步动作，并在有足够信息时直接收敛答案。'}
                                </div>
                              </div>
                            ) : (
                              <div className="rounded-[22px] border border-dashed border-black/10 px-4 py-4 text-sm text-muted-foreground dark:border-white/10">
                                提交任务后，执行步骤、状态和结果摘要会显示在这里。
                              </div>
                            )}

                            {agentRun && (
                            <div className="surface-panel rounded-[22px] px-4 py-4 dark:bg-[#182233]">
                              <button
                                onClick={() => setIsAgentTraceExpanded((prev) => !prev)}
                                className="flex w-full items-center justify-between text-left"
                              >
                                <div>
                                  <div className="text-sm font-medium text-foreground">处理过程</div>
                                  <div className="mt-1 text-xs text-muted-foreground">{agentTrace.length} 条记录</div>
                                </div>
                                <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", isAgentTraceExpanded && "rotate-180")} />
                              </button>

                              {isAgentTraceExpanded && (
                                <div className="mt-4 space-y-3">
                                  {agentTrace.map((item) => (
                                    <div key={item.id} className="flex items-start gap-3">
                                      <div className={cn(
                                        "mt-1.5 h-4 w-4 rounded-full border",
                                        item.tone === 'running' && "border-primary bg-primary/15",
                                        item.tone === 'success' && "border-emerald-500 bg-emerald-500/12",
                                        item.tone === 'error' && "border-destructive bg-destructive/12",
                                        (!item.tone || item.tone === 'neutral') && "border-border bg-transparent"
                                      )} />
                                      <div className="min-w-0 flex-1">
                                        <div className="text-sm font-medium text-foreground">{item.title}</div>
                                        {item.detail && <div className="mt-1 text-xs leading-5 text-muted-foreground">{item.detail}</div>}
                                      </div>
                                    </div>
                                  ))}
                                  {shownAgentSteps.length > 0 && (
                                    <div className="border-t soft-divider pt-4">
                                      <div className="space-y-3">
                                        {shownAgentSteps.map((step, index) => (
                                          <div key={step.step_id || index} className="rounded-[18px] bg-black/[0.02] px-3 py-3 dark:bg-white/[0.03]">
                                            <div className="text-sm font-medium text-foreground">{step.title}</div>
                                            <div className="mt-1 text-xs text-muted-foreground">
                                              {step.tool_name} · {AGENT_STEP_STATUS_LABEL[step.status]}
                                              {typeof step.latency_ms === 'number' ? ` · ${step.latency_ms}ms` : ''}
                                            </div>
                                            {step.observation && (
                                              <div className="mt-2 line-clamp-3 text-xs leading-5 text-muted-foreground">{step.observation}</div>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                            )}

                            {agentRun?.error && (
                              <div className="rounded-[22px] border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                                {agentRun.error.code}: {agentRun.error.message}
                              </div>
                            )}
                          </div>
                        )}

                        {isAgentWorkspace && sources.length > 0 && (
                          <div className="border-t soft-divider pt-1">
                            <div className="mb-2 flex items-center justify-between">
                              <div className="text-[11px] font-medium tracking-[0.08em] text-muted-foreground">
                                参考来源
                              </div>
                              <span className="text-[11px] text-muted-foreground">{sources.length} 条</span>
                            </div>
                          </div>
                        )}

                        {[{
                          title: '本地证据',
                          items: documentSources,
                        }, {
                          title: '外部参考',
                          items: webSources,
                        }].filter((section) => section.items.length > 0).map((section) => (
                          <div key={section.title}>
                            <div className="mb-2 flex items-center justify-between">
                              <div className="text-[11px] font-medium tracking-[0.08em] text-muted-foreground">
                                {section.title}
                              </div>
                              <span className="text-[11px] text-muted-foreground">{section.items.length} 条</span>
                            </div>
                            <div className="space-y-1.5">
                              {section.items.map((source) => {
                                const originalIndex = sources.indexOf(source)
                                const isExpanded = expandedSourceIndex === originalIndex
                                return (
                                  <div
                                    key={`${section.title}-${originalIndex}`}
                                    className="rounded-[18px] px-2.5 py-2.5 text-xs transition-colors hover:bg-black/[0.025]"
                                  >
                                    <div
                                      className="cursor-pointer"
                                      onClick={() => setExpandedSourceIndex(isExpanded ? null : originalIndex)}
                                    >
                                      <div className="flex items-start gap-2.5">
                                        <span className="mt-0.5 inline-flex min-w-5 items-center justify-center text-[11px] font-medium text-muted-foreground">
                                          {originalIndex + 1}
                                        </span>
                                        <motion.button
                                          className="mt-1"
                                          onClick={() => setExpandedSourceIndex(isExpanded ? null : originalIndex)}
                                          animate={{ rotate: isExpanded ? 90 : 0 }}
                                          transition={{ duration: 0.2 }}
                                        >
                                          <ChevronRight className="h-3 w-3 text-muted-foreground" />
                                        </motion.button>
                                        <div className="min-w-0 flex-1">
                                          <div className="flex items-start justify-between gap-2">
                                            <p className="break-words text-[13px] font-semibold leading-5 text-foreground" title={source.source}>
                                              {source.source}
                                            </p>
                                            {typeof source.relevance_score === 'number' && (
                                              <span className="shrink-0 text-[10px] tabular-nums text-muted-foreground">
                                                {(source.relevance_score * 100).toFixed(1)}%
                                              </span>
                                            )}
                                          </div>
                                          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                                            {source.type === 'web' && <Globe className="h-3 w-3 text-primary" />}
                                            {source.source_type && (
                                              <span>
                                                {{
                                                  academic: '学术',
                                                  news: '新闻',
                                                  official: '官方',
                                                  general: '网络',
                                                }[source.source_type] || '网络'}
                                              </span>
                                            )}
                                            {source.source_type && <span>·</span>}
                                            <span>{source.type === 'web' ? '网页' : '文档'}</span>
                                          </div>
                                          <p className="mt-2 text-[12px] leading-5 text-muted-foreground">
                                            {isExpanded
                                              ? source.content
                                              : `${(source.content || '').slice(0, 220)}${(source.content || '').length > 220 ? '...' : ''}`}
                                          </p>
                                        </div>
                                      </div>
                                    </div>
                                    {source.url && (
                                      <a
                                        href={source.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        onClick={(e) => e.stopPropagation()}
                                        className="ml-8 mt-2 inline-flex items-center text-[11px] text-primary hover:text-primary/80"
                                      >
                                        查看来源
                                      </a>
                                    )}
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        ))}
                      </motion.div>
                    </ScrollArea>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}
        </div>
      </div>
  )
}
