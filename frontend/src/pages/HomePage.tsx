import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, FileText, MessageSquare, Search } from 'lucide-react'

const ENTRY_POINTS = [
  {
    id: 'chat',
    title: '智能问答',
    description: '快速提问、连续追问和多轮研究讨论。',
    route: '/chat',
    icon: MessageSquare,
  },
  {
    id: 'agent',
    title: 'Agent 任务',
    description: '让 Geo-Agent 规划步骤、调用工具并生成任务结果。',
    route: '/chat',
    icon: Search,
  },
  {
    id: 'documents',
    title: '文献管理',
    description: '浏览、整理和维护本地知识库与文档来源。',
    route: '/documents',
    icon: FileText,
  },
]

export default function HomePage() {
  const navigate = useNavigate()

  return (
    <div className="relative flex h-full min-h-full items-center justify-center overflow-hidden px-6 py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(103,153,255,0.05),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(69,101,177,0.07),transparent_22%)]" />

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: 'easeOut' }}
        className="relative mx-auto w-full max-w-[1080px]"
      >
        <div className="workbench-panel overflow-hidden rounded-[36px] px-8 py-8 md:px-10 md:py-10">
          <div className="grid gap-10 lg:grid-cols-[1.2fr_0.9fr] lg:items-end">
            <div className="max-w-[640px]">
              <div className="inline-flex items-center gap-2 rounded-full border border-black/5 bg-slate-50 px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Geo-Agent
              </div>
              <h1 className="mt-6 max-w-[11ch] text-[clamp(2.6rem,6vw,5rem)] font-semibold leading-[1.02] text-foreground">
                A focused research workspace for geology.
              </h1>
              <p className="mt-5 max-w-[56ch] text-[15px] leading-7 text-muted-foreground md:text-[16px]">
                面向文献问答、证据检索与任务执行的研究工作台。把主要注意力留给问题、来源与结果，而不是界面装饰。
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <button
                  onClick={() => navigate('/chat')}
                  className="inline-flex items-center gap-2 rounded-[22px] bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground transition-transform duration-200 hover:scale-[1.01] hover:bg-primary/90"
                >
                  进入研究工作台
                  <ArrowRight className="h-4 w-4" />
                </button>
                <button
                  onClick={() => navigate('/documents')}
                  className="inline-flex items-center gap-2 rounded-[22px] border border-black/5 bg-slate-50 px-5 py-3 text-sm font-medium text-foreground transition-colors hover:bg-slate-100"
                >
                  查看文献库
                </button>
              </div>
            </div>

            <div className="grid gap-3">
              {ENTRY_POINTS.map((item, index) => {
                const Icon = item.icon
                return (
                  <motion.button
                    key={item.id}
                    initial={{ opacity: 0, x: 16 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.08 * index, duration: 0.35, ease: 'easeOut' }}
                    onClick={() => navigate(item.route)}
                    className="source-card group flex items-center justify-between rounded-[26px] px-5 py-4 text-left transition-colors hover:bg-slate-50"
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex h-11 w-11 items-center justify-center rounded-[18px] bg-slate-50 text-primary">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-foreground">{item.title}</div>
                        <div className="mt-1 text-xs leading-5 text-muted-foreground">{item.description}</div>
                      </div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-foreground" />
                  </motion.button>
                )
              })}
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
