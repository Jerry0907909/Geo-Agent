import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { MessageSquare, Search, FileText } from 'lucide-react'
import { useState } from 'react'
import { useThemeStore } from '@/store/useThemeStore'

interface FeatureCard {
  id: string
  title: string
  description: string
  icon: React.ReactNode
  route: string
  accentColor: string
  gradientFrom: string
  gradientTo: string
  decoratorColor: string
}

// 装饰性引号组件
const QuoteDecorator = ({ color }: { color: string }) => (
  <svg 
    width="32" 
    height="24" 
    viewBox="0 0 32 24" 
    fill="none" 
    className="absolute top-4 left-4"
  >
    <path 
      d="M0 24V14.4C0 10.4 0.8 7.2 2.4 4.8C4.08 2.4 6.72 0.64 10.32 -0.48L12 3.36C9.84 4.16 8.16 5.28 6.96 6.72C5.84 8.08 5.28 9.68 5.28 11.52H10.56V24H0ZM19.44 24V14.4C19.44 10.4 20.24 7.2 21.84 4.8C23.52 2.4 26.16 0.64 29.76 -0.48L31.44 3.36C29.28 4.16 27.6 5.28 26.4 6.72C25.28 8.08 24.72 9.68 24.72 11.52H30V24H19.44Z" 
      fill={color}
      fillOpacity="0.15"
    />
  </svg>
)

export default function HomePage() {
  const navigate = useNavigate()
  const { theme } = useThemeStore()
  const [hoveredCard, setHoveredCard] = useState<string | null>(null)

  const features: FeatureCard[] = [
    {
      id: 'chat',
      title: '智能问答',
      description: '与 AI 助手对话，获取地质文献相关问题的专业解答',
      icon: <MessageSquare className="w-7 h-7" strokeWidth={1.5} />,
      route: '/chat',
      accentColor: '#3B82F6',
      gradientFrom: '#3B82F6',
      gradientTo: '#6366F1',
      decoratorColor: '#3B82F6'
    },
    {
      id: 'search',
      title: '文献检索',
      description: '快速搜索和查找地质相关的学术文献与资料',
      icon: <Search className="w-7 h-7" strokeWidth={1.5} />,
      route: '/search',
      accentColor: '#10B981',
      gradientFrom: '#10B981',
      gradientTo: '#059669',
      decoratorColor: '#10B981'
    },
    {
      id: 'documents',
      title: '文献管理',
      description: '管理、组织和查看您的地质文献收藏',
      icon: <FileText className="w-7 h-7" strokeWidth={1.5} />,
      route: '/documents',
      accentColor: '#8B5CF6',
      gradientFrom: '#8B5CF6',
      gradientTo: '#A855F7',
      decoratorColor: '#8B5CF6'
    }
  ]

  const handleCardClick = (route: string) => {
    navigate(route)
  }

  return (
    <div className={`relative w-full min-h-screen overflow-hidden transition-colors duration-500 ${
      theme === 'dark' 
        ? 'bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900' 
        : 'bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/40'
    }`}>
      {/* 柔和背景装饰 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className={`absolute -top-1/3 -right-1/4 w-[600px] h-[600px] rounded-full blur-[120px] ${
          theme === 'dark' 
            ? 'bg-blue-500/5' 
            : 'bg-blue-200/40'
        }`} />
        <div className={`absolute -bottom-1/3 -left-1/4 w-[500px] h-[500px] rounded-full blur-[100px] ${
          theme === 'dark'
            ? 'bg-purple-500/5'
            : 'bg-purple-200/30'
        }`} />
      </div>

      {/* 主内容区 */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-8 py-12">
        {/* 标题区域 */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="text-center mb-16"
        >
          <h1 className={`text-4xl md:text-5xl font-semibold mb-4 tracking-tight ${
            theme === 'dark' ? 'text-white' : 'text-slate-800'
          }`}>
            Geo-Agent
          </h1>
          <p className={`text-base md:text-lg font-light ${
            theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
          }`}>
            选择一个功能开始您的探索之旅
          </p>
        </motion.div>

        {/* 功能卡片网格 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8 max-w-5xl w-full px-4">
          {features.map((feature, index) => (
            <motion.div
              key={feature.id}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.5,
                delay: index * 0.1,
                ease: [0.25, 0.46, 0.45, 0.94]
              }}
              whileHover={{
                y: -8,
                transition: { duration: 0.3, ease: 'easeOut' }
              }}
              onHoverStart={() => setHoveredCard(feature.id)}
              onHoverEnd={() => setHoveredCard(null)}
              onClick={() => handleCardClick(feature.route)}
              className="relative cursor-pointer group"
            >
              {/* 卡片主体 */}
              <div 
                className={`relative overflow-hidden rounded-2xl p-6 md:p-8 h-full min-h-[280px] flex flex-col transition-all duration-300 ${
                  theme === 'dark'
                    ? 'bg-gradient-to-br from-slate-800/80 to-slate-800/40 border border-slate-700/50'
                    : 'bg-gradient-to-br from-white to-slate-50/80 border border-slate-100'
                }`}
                style={{
                  boxShadow: hoveredCard === feature.id
                    ? theme === 'dark'
                      ? '0 20px 40px -12px rgba(0, 0, 0, 0.4), 0 8px 16px -8px rgba(0, 0, 0, 0.3)'
                      : '0 20px 40px -12px rgba(0, 0, 0, 0.12), 0 8px 16px -8px rgba(0, 0, 0, 0.08)'
                    : theme === 'dark'
                      ? '0 4px 20px -4px rgba(0, 0, 0, 0.3), 0 2px 8px -2px rgba(0, 0, 0, 0.2)'
                      : '0 4px 20px -4px rgba(0, 0, 0, 0.06), 0 2px 8px -2px rgba(0, 0, 0, 0.04)'
                }}
              >
                {/* 装饰性引号 */}
                <QuoteDecorator color={feature.decoratorColor} />

                {/* 顶部渐变装饰线 */}
                <div 
                  className="absolute top-0 left-0 right-0 h-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                  style={{
                    background: `linear-gradient(90deg, ${feature.gradientFrom}, ${feature.gradientTo})`
                  }}
                />

                {/* 图标容器 */}
                <motion.div
                  className="relative w-14 h-14 rounded-xl flex items-center justify-center mb-5 mt-6"
                  style={{
                    background: `linear-gradient(135deg, ${feature.gradientFrom}, ${feature.gradientTo})`,
                    boxShadow: `0 8px 24px -4px ${feature.accentColor}40`
                  }}
                  animate={hoveredCard === feature.id ? {
                    scale: [1, 1.05, 1],
                  } : {}}
                  transition={{ duration: 0.4 }}
                >
                  <div className="text-white">
                    {feature.icon}
                  </div>
                  
                  {/* 图标光泽效果 */}
                  <div className="absolute inset-0 rounded-xl overflow-hidden">
                    <div className="absolute top-0 left-0 right-0 h-1/2 bg-gradient-to-b from-white/20 to-transparent" />
                  </div>
                </motion.div>

                {/* 标题 */}
                <h3 className={`text-xl font-semibold mb-2 tracking-tight ${
                  theme === 'dark' ? 'text-white' : 'text-slate-800'
                }`}>
                  {feature.title}
                </h3>

                {/* 描述文字 */}
                <p className={`text-sm leading-relaxed font-light flex-1 ${
                  theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
                }`}>
                  {feature.description}
                </p>

                {/* 悬停时的箭头指示 */}
                <motion.div
                  className={`mt-4 flex items-center gap-1 text-sm font-medium ${
                    theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
                  }`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={hoveredCard === feature.id ? { opacity: 1, x: 0 } : { opacity: 0, x: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  <span style={{ color: feature.accentColor }}>开始使用</span>
                  <motion.span
                    animate={hoveredCard === feature.id ? { x: [0, 4, 0] } : {}}
                    transition={{ duration: 0.8, repeat: Infinity }}
                    style={{ color: feature.accentColor }}
                  >
                    →
                  </motion.span>
                </motion.div>

                {/* 背景装饰圆 */}
                <div 
                  className="absolute -bottom-16 -right-16 w-40 h-40 rounded-full opacity-5 group-hover:opacity-10 transition-opacity duration-500"
                  style={{ background: feature.accentColor }}
                />
              </div>
            </motion.div>
          ))}
        </div>

        {/* 底部提示 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.6 }}
          className={`mt-12 text-sm font-light ${
            theme === 'dark' ? 'text-slate-500' : 'text-slate-400'
          }`}
        >
          悬停卡片查看更多效果
        </motion.div>
      </div>
    </div>
  )
}
