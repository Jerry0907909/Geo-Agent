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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, Send, BookOpen, MessageCircle, Search, Sparkles, ChevronRight, ChevronDown, PanelRightClose, PanelRightOpen, Globe, Copy, Check, X, ThumbsUp, ThumbsDown, RotateCcw, ArrowRight, Square, Route, ListTree, FileText } from "lucide-react"
import Markdown from "react-markdown"
import { useChatStore } from "@/store/useChatStore"
import { motion, AnimatePresence } from "framer-motion"
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
  const [webSearchEnabled, setWebSearchEnabled] = useState(false)
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
              allow_web_search: webSearchEnabled,
              return_steps: true,
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
            web_search: webSearchEnabled,
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
  }, [input, isLoading, currentConversationId, mode, loadConversations, setCurrentConversationId, selectedImage, imagePreview, topK, minRelevanceScore, webSearchEnabled, navigate, generateFollowUpQuestions, agentRun?.run_id, setSearchParams, appendAgentTrace])

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
  const isAgentActive = agentRun?.status === 'queued' || agentRun?.status === 'planning' || agentRun?.status === 'running'
  const contentMaxWidth = mode === 'agent'
    ? "max-w-[980px] xl:max-w-[1040px] 2xl:max-w-[1080px]"
    : "max-w-[860px] xl:max-w-[880px] 2xl:max-w-[880px]"
  const composeMaxWidth = mode === 'agent' ? "max-w-[980px]" : "max-w-[860px]"
  const proseWidth = mode === 'agent' ? "max-w-[920px]" : "max-w-[860px]"
  const currentModeConfig = MODE_CONFIG[mode]
  const markdownComponents = {
    p: ({ children }: any) => <p className="mb-4 last:mb-0">{children}</p>,
    ul: ({ children }: any) => <ul className="mb-4 list-disc space-y-1.5 pl-5">{children}</ul>,
    ol: ({ children }: any) => <ol className="mb-4 list-decimal space-y-1.5 pl-5">{children}</ol>,
    li: ({ children }: any) => <li className="leading-8">{children}</li>,
    code: ({ inline, children, ...props }: any) => (
      inline ? (
        <code className="rounded-md bg-muted px-1.5 py-0.5 text-sm text-foreground" {...props}>
          {children}
        </code>
      ) : (
        <code className="mb-4 block overflow-x-auto rounded-2xl border border-border bg-card p-4 text-sm text-foreground shadow-sm" {...props}>
          {children}
        </code>
      )
    ),
  }

  return (
    <div className="flex h-full w-full overflow-hidden bg-transparent">
      <div className="flex h-full w-full overflow-hidden">
        <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden bg-background">
          <ScrollArea className="flex-1">
            <div className={cn("mx-auto flex w-full flex-col gap-8 px-4 pb-24 pt-8 md:px-6", contentMaxWidth)}>
                {showWelcome && (
                  <div className={cn("mx-auto flex min-h-[62vh] w-full flex-col items-center justify-center gap-4 py-6 animate-in fade-in duration-300", composeMaxWidth)}>
                    <div className="text-center">
                      <div className="inline-flex items-center gap-2 text-[18px] font-semibold tracking-[-0.01em] text-foreground md:text-[20px]">
                        <currentModeConfig.icon className="h-5 w-5 text-primary" />
                        <span>{currentModeConfig.label}</span>
                      </div>
                    </div>

                    <div className={cn("floating-compose w-full rounded-[26px] px-4 py-3", mode === 'agent' ? "max-w-[840px]" : "max-w-[760px]")}>
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

                      <div className="flex items-end gap-2 px-1 py-0.5">
                        <textarea
                          value={input}
                          onChange={(e) => setInput(e.target.value)}
                          onKeyDown={handleKeyDown}
                          onPaste={handlePaste}
                          placeholder={selectedImage ? "描述你想了解的内容..." : "给 Geo-Agent 发送消息"}
                          rows={2}
                          className="min-h-[62px] flex-1 resize-none bg-transparent border-none text-[16px] leading-7 text-foreground placeholder:text-muted-foreground/75 focus:outline-none"
                          style={{ maxHeight: "180px" }}
                        />
                        <motion.button
                          onClick={() => handleSubmit()}
                          disabled={isLoading || (!input.trim() && !selectedImage)}
                          whileHover={{ scale: isLoading || (!input.trim() && !selectedImage) ? 1 : 1.03 }}
                          whileTap={{ scale: isLoading || (!input.trim() && !selectedImage) ? 1 : 0.97 }}
                          className="mb-1 flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-all duration-200 hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-45"
                        >
                          <Send className="h-4 w-4" />
                        </motion.button>
                      </div>

                      <div className="mt-1 flex items-center justify-between border-t soft-divider px-1.5 pt-1.5">
                        <div className="flex items-center gap-1.5 overflow-x-auto">
                          {(Object.entries(MODE_CONFIG) as [ChatMode, typeof MODE_CONFIG.chat][]).map(([key, config]) => {
                            const Icon = config.icon
                            return (
                              <button
                                key={key}
                                onClick={() => setMode(key)}
                                className={cn("deep-chip !rounded-lg !px-2.5 !py-1", mode === key && "deep-chip-active")}
                                title={config.description}
                              >
                                <Icon className="h-3 w-3" />
                                <span>{config.label}</span>
                              </button>
                            )
                          })}
                          <button
                            onClick={() => setWebSearchEnabled(!webSearchEnabled)}
                            className={cn("deep-chip !rounded-lg !px-2.5 !py-1", webSearchEnabled && "deep-chip-active")}
                            title={webSearchEnabled ? '关闭网络搜索' : '启用网络搜索'}
                          >
                            <Globe className="h-3 w-3" />
                            <span>网络</span>
                          </button>
                          {mode === 'rag' && (
                            <button
                              onClick={() => setShowRagSettings(!showRagSettings)}
                              className={cn("deep-chip !rounded-lg !px-2.5 !py-1", showRagSettings && "deep-chip-active")}
                              title="检索设置"
                            >
                              <ChevronRight className={cn("h-3 w-3 transition-transform", showRagSettings && "rotate-90")} />
                            </button>
                          )}
                        </div>
                        <span className="pl-2 text-[11px] text-muted-foreground">Enter</span>
                      </div>
                    </div>
                  </div>
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
                        <div className="relative pl-2">
                          <div className="mb-4 flex items-center gap-3">
                            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/12 text-primary">
                              <Sparkles className="h-4 w-4" />
                            </div>
                            <p className="text-sm font-semibold text-foreground">Geo-Agent</p>
                          </div>

                          <div className={cn("prose-refined prose", proseWidth)}>
                            {isStreamingMessage ? (
                              <div className="leading-8">
                                <Markdown
                                  className={cn("prose-refined prose leading-8", proseWidth)}
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
                                className={cn("prose-refined prose leading-8", proseWidth)}
                                components={markdownComponents}
                              >
                                {msg.content}
                              </Markdown>
                            )}
                          </div>

                          {!isWelcomeMessage && !isLoading && (
                            <div className="mt-5 flex items-center gap-1.5 border-t soft-divider pt-4">
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
                            <div className="mt-6 space-y-2">
                              {followUpQuestions.map((question, qIndex) => (
                                <button
                                  key={qIndex}
                                  onClick={() => handleFollowUpClick(question)}
                                  className="group flex w-full items-center gap-2 rounded-2xl border border-border bg-card px-4 py-3 text-left text-sm text-foreground transition-all duration-200 hover:border-primary/30 hover:bg-accent/35"
                                >
                                  <span className="flex-1">{question}</span>
                                  <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="flex flex-col items-end">
                          <div className="inline-block max-w-[76%] rounded-xl border border-border bg-muted px-4 py-3 text-foreground">
                            {msg.metadata?.image && (
                              <img
                                src={msg.metadata.image}
                                alt="用户上传的图片"
                                className="mb-3 max-h-64 max-w-full rounded-2xl border border-border"
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
                {agentRun && (
                  <Card className="shell-panel rounded-[24px] border">
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1.5">
                          <CardTitle className="font-display text-[1.05rem]">Agent 执行面板</CardTitle>
                          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                            {(agentRun.status === 'planning' || agentRun.status === 'running' || agentRun.status === 'queued') && (
                              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                            )}
                            <span>{AGENT_STATUS_LABEL[agentRun.status]}</span>
                            <span>· {completedAgentSteps} 已完成</span>
                            {failedAgentSteps > 0 && <span>· {failedAgentSteps} 失败</span>}
                            {agentRun.execution_time && <span>· {agentRun.execution_time.toFixed(2)}s</span>}
                          </div>
                        </div>
                        {(agentRun.status === 'queued' || agentRun.status === 'planning' || agentRun.status === 'running') && (
                          <button
                            onClick={handleCancelAgentRun}
                            className="inline-flex items-center gap-1 rounded-md border border-border bg-card px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                          >
                            <Square className="h-3 w-3" />
                            取消
                          </button>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3.5">
                      <div className="grid gap-3 xl:grid-cols-[1.1fr_1fr_1.2fr]">
                        <div className="rounded-2xl border border-border/70 bg-card px-4 py-3.5">
                          <div className="mb-2 flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                            <Route className="h-3.5 w-3.5" />
                            Route
                          </div>
                          <div className="text-sm font-medium text-foreground">
                            {agentRouteInfo?.summary || agentRun.plan_summary || '正在识别任务路径'}
                          </div>
                          {agentRouteInfo?.reason && (
                            <div className="mt-1.5 line-clamp-3 text-xs leading-5 text-muted-foreground">
                              {agentRouteInfo.reason}
                            </div>
                          )}
                        </div>

                        <div className="rounded-2xl border border-border/70 bg-card px-4 py-3.5">
                          <div className="mb-2 flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                            <ListTree className="h-3.5 w-3.5" />
                            Current Step
                          </div>
                          <div className="text-sm font-medium text-foreground">
                            {currentAgentStep?.title || latestAgentStep?.title || statusMessage || AGENT_STATUS_LABEL[agentRun.status]}
                          </div>
                          <div className="mt-1.5 text-xs leading-5 text-muted-foreground">
                            {currentAgentStep?.goal || latestAgentStep?.goal || statusMessage || '等待规划输出'}
                          </div>
                        </div>

                        <div className="rounded-2xl border border-border/70 bg-card px-4 py-3.5">
                          <div className="mb-2 flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                            <FileText className="h-3.5 w-3.5" />
                            Synthesis
                          </div>
                          <div className="text-sm font-medium text-foreground">
                            {synthesisPreview
                              ? '正在汇总最终回答'
                              : agentRun.status === 'completed'
                                ? '已生成最终回答'
                                : '尚未进入回答汇总'}
                          </div>
                          <div className="mt-1.5 line-clamp-4 text-xs leading-5 text-muted-foreground">
                            {synthesisPreview || '执行阶段完成后会在这里实时显示最终回答的生成过程。'}
                          </div>
                        </div>
                      </div>

                      {(agentTrace.length > 0 || shownAgentSteps.length > 0) ? (
                        <div className="overflow-hidden rounded-2xl border border-border/70 bg-card">
                          <button
                            onClick={() => setIsAgentTraceExpanded((prev) => !prev)}
                            className="flex w-full items-center justify-between border-b soft-divider px-4 py-3 text-left transition-colors hover:bg-accent/30"
                          >
                            <div className="flex min-w-0 items-center gap-3">
                              <div>
                                <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                                  Processing Trace
                                </div>
                                <div className="mt-1 text-sm font-medium text-foreground">
                                  {isAgentActive ? '实时显示任务处理过程' : '任务处理过程已收起，按需展开查看'}
                                </div>
                              </div>
                              <span className="rounded-full border border-border/80 px-2 py-0.5 text-[11px] text-muted-foreground">
                                {agentTrace.length} 条
                              </span>
                            </div>
                            <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", isAgentTraceExpanded && "rotate-180")} />
                          </button>

                          {isAgentTraceExpanded && (
                            <div className="space-y-1.5 px-3 py-3">
                              {agentTrace.map((item) => (
                                <div
                                  key={item.id}
                                  className={cn(
                                    "rounded-2xl border px-3.5 py-3",
                                    item.tone === 'running' && "border-primary/18 bg-primary/5",
                                    item.tone === 'success' && "border-emerald-200/70 bg-emerald-50/80 dark:border-emerald-900/60 dark:bg-emerald-950/20",
                                    item.tone === 'error' && "border-destructive/20 bg-destructive/5",
                                    (!item.tone || item.tone === 'neutral') && "border-border/70 bg-background/70"
                                  )}
                                >
                                  <div className="flex items-start gap-3">
                                    <div className={cn(
                                      "mt-1 h-2.5 w-2.5 rounded-full",
                                      item.tone === 'running' && "bg-primary",
                                      item.tone === 'success' && "bg-emerald-500",
                                      item.tone === 'error' && "bg-destructive",
                                      (!item.tone || item.tone === 'neutral') && "bg-muted-foreground/45"
                                    )} />
                                    <div className="min-w-0 flex-1">
                                      <div className="text-sm font-medium text-foreground">{item.title}</div>
                                      {item.detail && (
                                        <div className="mt-1.5 text-xs leading-5 text-muted-foreground">
                                          {item.detail}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}

                              {shownAgentSteps.length > 0 && (
                                <div className="rounded-2xl border border-border/70 bg-background/70 px-3.5 py-3">
                                  <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                                    Step Snapshot
                                  </div>
                                  <div className="space-y-2">
                                    {shownAgentSteps.map((step, index) => (
                                      <div
                                        key={step.step_id || index}
                                        className="rounded-xl border border-border/60 px-3 py-2.5"
                                      >
                                        <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                                          <div className="font-medium text-foreground">{step.title}</div>
                                          <div className="text-xs text-muted-foreground">
                                            {step.tool_name} · {AGENT_STEP_STATUS_LABEL[step.status]}
                                            {typeof step.latency_ms === 'number' ? ` · ${step.latency_ms}ms` : ''}
                                          </div>
                                        </div>
                                        {(step.goal || step.observation) && (
                                          <div className="mt-1.5 space-y-1">
                                            {step.goal && (
                                              <div className="text-xs leading-5 text-muted-foreground/90">{step.goal}</div>
                                            )}
                                            {step.observation && (
                                              <div className="line-clamp-2 text-xs leading-5 text-muted-foreground">{step.observation}</div>
                                            )}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ) : (
                        isAgentActive && (
                          <div className="rounded-2xl border border-dashed border-border/80 px-4 py-3 text-xs text-muted-foreground">
                            暂无处理过程，正在生成执行计划...
                          </div>
                        )
                      )}

                      {agentRun.error && (
                        <div className="rounded-2xl border border-destructive/20 bg-destructive/5 px-3.5 py-3 text-sm text-destructive">
                          {agentRun.error.code}: {agentRun.error.message}
                        </div>
                      )}

                      {isAgentActive && synthesisPreview && (
                        <div className="rounded-2xl border border-border/70 bg-card px-4 py-3.5">
                          <div className="mb-2 flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                            <FileText className="h-3.5 w-3.5" />
                            Live Synthesis
                          </div>
                          <Markdown className="prose-refined prose max-w-none leading-8">
                            {synthesisPreview}
                          </Markdown>
                          <motion.span
                            className="ml-1 mt-1 inline-block h-5 w-0.5 bg-primary"
                            animate={{ opacity: [1, 0] }}
                            transition={{ duration: 0.8, repeat: Infinity }}
                          />
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}
                {isLoading && !streamingContent && mode !== 'agent' && (
                  <div className="flex items-center gap-2 rounded-full bg-card px-3 py-2 text-sm shadow-sm animate-in fade-in duration-200">
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
            <div className="border-t soft-divider bg-background px-3 pb-4 pt-3">
              <div className={cn("mx-auto space-y-2.5", composeMaxWidth)}>
                <AnimatePresence>
                  {mode === 'rag' && showRagSettings && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
                      className="shell-panel overflow-hidden rounded-xl p-3.5 space-y-3"
                    >
                    <div className="mb-2 text-xs font-medium text-muted-foreground">检索设置</div>
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
                
                <div className="floating-compose rounded-xl px-2.5 py-2 transition-all duration-200 hover:border-primary/30">
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
                  
                  <div className="flex items-end gap-2 px-1 py-0.5">
                    <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      onPaste={handlePaste}
                      placeholder={selectedImage ? "描述你想了解的内容..." : "给 Geo-Agent 发送消息"}
                      rows={2}
                      className="min-h-[42px] flex-1 resize-none bg-transparent border-none text-[15px] leading-6 text-foreground placeholder:text-muted-foreground/85 focus:outline-none"
                      style={{ maxHeight: '180px' }}
                    />
                    <motion.button
                      onClick={() => handleSubmit()}
                      disabled={isLoading || (!input.trim() && !selectedImage)}
                      whileHover={{ scale: isLoading || (!input.trim() && !selectedImage) ? 1 : 1.05 }}
                      whileTap={{ scale: isLoading || (!input.trim() && !selectedImage) ? 1 : 0.95 }}
                      className="mb-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-all duration-200 hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-45"
                    >
                      <Send className="h-3.5 w-3.5" />
                    </motion.button>
                  </div>

                  <div className="mt-1 flex items-center justify-between border-t soft-divider px-1.5 pt-1.5">
                    <div className="flex items-center gap-1.5 overflow-x-auto">
                      {(Object.entries(MODE_CONFIG) as [ChatMode, typeof MODE_CONFIG.chat][]).map(([key, config]) => {
                        const Icon = config.icon
                        return (
                          <button
                            key={key}
                            onClick={() => setMode(key)}
                            className={cn("deep-chip !rounded-lg !px-2.5 !py-1", mode === key && "deep-chip-active")}
                            title={config.description}
                          >
                            <Icon className="h-3 w-3" />
                            <span>{config.label}</span>
                          </button>
                        )
                      })}
                      <button
                        onClick={() => setWebSearchEnabled(!webSearchEnabled)}
                        className={cn("deep-chip !rounded-lg !px-2.5 !py-1", webSearchEnabled && "deep-chip-active")}
                        title={webSearchEnabled ? '关闭网络搜索' : '启用网络搜索'}
                      >
                        <Globe className="h-3 w-3" />
                        <span>网络</span>
                      </button>
                      {mode === 'rag' && (
                        <button
                          onClick={() => setShowRagSettings(!showRagSettings)}
                          className={cn("deep-chip !rounded-lg !px-2.5 !py-1", showRagSettings && "deep-chip-active")}
                          title="检索设置"
                        >
                          <ChevronRight className={cn("h-3 w-3 transition-transform", showRagSettings && "rotate-90")} />
                        </button>
                      )}
                    </div>
                    <span className="pl-2 text-[11px] text-muted-foreground">Enter 发送</span>
                  </div>
                </div>
              </div>
            </div>
            )}
          </div>

          {sources.length > 0 && (
            <motion.div 
              initial={{ width: 56 }}
              animate={{ width: isSourcesOpen ? sourcePanelWidth : 56 }}
              transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
              className="relative m-3 ml-0 hidden flex-col overflow-hidden rounded-xl shell-panel lg:flex"
            >
              {isSourcesOpen && (
                <div
                  onMouseDown={handleSourceResizeStart}
                  className={cn(
                    "absolute left-0 top-0 z-20 h-full w-2 -translate-x-1/2 cursor-col-resize",
                    isResizingSources ? "bg-primary/15" : "bg-transparent hover:bg-primary/10"
                  )}
                  title="拖拽调整宽度"
                />
              )}
              <div className="flex items-center gap-2 border-b soft-divider bg-card px-3 py-2 font-medium">
                <motion.button
                  onClick={() => setIsSourcesOpen(!isSourcesOpen)}
                  className="rounded-lg p-1 transition-colors hover:bg-muted/70"
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
                      <span className="text-sm">参考来源</span>
                      <span className="text-xs text-muted-foreground">({sources.length})</span>
                      <span className="text-[11px] text-muted-foreground">与回答中的 [n] 一一对应</span>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              <AnimatePresence>
                {isSourcesOpen && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="flex-1 overflow-hidden"
                  >
                    <ScrollArea className="h-full">
                      <motion.div className="divide-y divide-border/80">
                        {sources.map((source, i) => (
                          <motion.div
                            key={i}
                            variants={{
                              hidden: { opacity: 0, y: 20 },
                              visible: { opacity: 1, y: 0 }
                            }}
                            transition={{ duration: 0.3 }}
                          >
                            <div className="px-3 py-1.5 text-xs">
                                <div
                                  className="cursor-pointer rounded-lg px-1 py-2 transition-colors hover:bg-accent/35"
                                  onClick={() => setExpandedSourceIndex(expandedSourceIndex === i ? null : i)}
                                >
                                  <div className="flex items-start gap-2.5">
                                  <span className="mt-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded border border-primary/20 bg-primary/10 px-1 text-[10px] font-semibold text-primary">
                                    [{i + 1}]
                                  </span>
                                  <motion.button
                                    className="mt-0.5"
                                    onClick={() => setExpandedSourceIndex(expandedSourceIndex === i ? null : i)}
                                    animate={{ rotate: expandedSourceIndex === i ? 90 : 0 }}
                                    transition={{ duration: 0.2 }}
                                  >
                                    <ChevronRight className="h-3 w-3 text-muted-foreground" />
                                  </motion.button>
                                    <div className="min-w-0 flex-1 overflow-hidden">
                                      <div className="mb-1.5 flex items-start justify-between gap-2">
                                        <div className="min-w-0 flex-1">
                                          <p className="break-words text-[13px] font-semibold leading-5 text-foreground" title={source.source}>
                                            {source.source}
                                          </p>
                                        </div>
                                        {typeof source.relevance_score === 'number' && (
                                          <span className="shrink-0 rounded border border-primary/20 bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-primary">
                                            {(source.relevance_score * 100).toFixed(1)}%
                                          </span>
                                        )}
                                      </div>
                                      <div className="mb-1.5 flex items-center gap-2 text-[11px] text-muted-foreground">
                                      {source.type === 'web' && <Globe className="h-3 w-3 text-primary" />}
                                      {source.source_type && (
                                        <span className="rounded bg-muted px-1.5 py-0.5">
                                          {{
                                            'academic': '学术',
                                            'news': '新闻',
                                            'official': '官方',
                                            'general': '网络',
                                          }[source.source_type] || '网络'}
                                        </span>
                                      )}
                                      {typeof source.relevance_score === 'number' && (
                                        <span className="tabular-nums">
                                          相关度 {(source.relevance_score * 100).toFixed(1)}%
                                        </span>
                                      )}
                                    </div>
                                    {typeof source.relevance_score === 'number' && (
                                      <div className="mb-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                                        <div
                                          className="h-full rounded-full bg-primary/60"
                                          style={{ width: `${Math.max(4, Math.min(source.relevance_score * 100, 100))}%` }}
                                        />
                                      </div>
                                    )}
                                    <p className="mt-1.5 text-[12px] leading-5 text-muted-foreground">
                                      {expandedSourceIndex === i
                                        ? source.content
                                        : `${(source.content || '').slice(0, 220)}${(source.content || '').length > 220 ? '...' : ''}`}
                                    </p>
                                  </div>
                                </div>
                                {source.url && (
                                  <a
                                    href={source.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                    className="ml-8 mt-1 inline-flex items-center rounded-md border border-border px-2 py-0.5 text-[11px] text-primary hover:bg-primary/10"
                                  >
                                    查看来源
                                  </a>
                                )}
                              </div>
                            </div>
                          </motion.div>
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
