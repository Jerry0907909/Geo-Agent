import React, { useState, useEffect, useCallback } from "react"
import { chatService, type Document, type Collection, type FileTypeStat } from "@/services/api"
import { motion, AnimatePresence } from "framer-motion"
import { 
  Upload, FileText, Trash2, RefreshCw, Loader2, Database, Eye, Edit, Save, X,
  FileType, File, FileSpreadsheet, Presentation, FileCode, Files, FolderOpen,
  CheckCircle, AlertCircle, Plus, Pencil
} from "lucide-react"
import { cn } from "@/lib/utils"

// ==================== 设计系统常量 ====================
const colors = {
  primary: "#165DFF",
  primaryHover: "#0E4BD9",
  danger: "#F53F3F",
  dangerHover: "#CB2E2E",
  // 浅色模式
  bgLight: "#F5F7FA",
  bgCard: "#FFFFFF",
  border: "#E5E6EB",
  textTitle: "#1D2129",
  textBody: "#4E5969",
  textMuted: "#86909C",
  shadow: "0 2px 8px rgba(0,0,0,0.06)",
  shadowHover: "0 4px 16px rgba(0,0,0,0.12)",
}

// ==================== 通用子组件 ====================

// 统计卡片组件
interface StatCardProps {
  title: string
  value: number
  icon: React.ReactNode
  color: string
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color }) => (
  <motion.div
    whileHover={{ y: -2, scale: 1.02 }}
    transition={{ duration: 0.3 }}
    className="bg-white dark:bg-slate-800 rounded-lg p-4 cursor-default shadow-sm dark:shadow-slate-900/30"
  >
    <div className="flex items-center justify-between">
      <div>
        <p className="text-xs mb-1 text-slate-500 dark:text-slate-400">{title}</p>
        <p className="text-2xl font-bold" style={{ color }}>{value}</p>
      </div>
      <div 
        className="h-10 w-10 rounded-lg flex items-center justify-center"
        style={{ backgroundColor: `${color}15` }}
      >
        <div style={{ color }}>{icon}</div>
      </div>
    </div>
  </motion.div>
)

// 文献卡片组件
interface LiteratureCardProps {
  doc: Document
  onView: () => void
  onDelete: () => void
  isDeleting: boolean
}

const LiteratureCard: React.FC<LiteratureCardProps> = ({ doc, onView, onDelete, isDeleting }) => {
  const [isHovered, setIsHovered] = useState(false)
  
  const getFileIcon = (type: string) => {
    const iconClass = "h-5 w-5"
    switch (type) {
      case 'markdown': return <FileCode className={iconClass} />
      case 'pdf': return <FileText className={iconClass} />
      case 'word': return <File className={iconClass} />
      case 'txt': return <FileType className={iconClass} />
      case 'excel': return <FileSpreadsheet className={iconClass} />
      case 'ppt': return <Presentation className={iconClass} />
      default: return <Files className={iconClass} />
    }
  }
  
  const getFileColor = (type: string) => {
    switch (type) {
      case 'markdown': return "#722ED1"
      case 'pdf': return "#F53F3F"
      case 'word': return "#165DFF"
      case 'txt': return "#86909C"
      case 'excel': return "#00B42A"
      case 'ppt': return "#FF7D00"
      default: return "#86909C"
    }
  }
  
  const fileType = doc.file_type || 'other'
  const fileColor = getFileColor(fileType)
  
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      className={cn(
        "bg-white dark:bg-slate-800 rounded-lg p-4 transition-all duration-300 cursor-pointer group",
        isHovered ? "shadow-lg dark:shadow-slate-900/50" : "shadow-sm dark:shadow-slate-900/30"
      )}
      style={{ borderLeft: `3px solid ${fileColor}` }}
      onClick={onView}
    >
      <div className="flex items-start gap-3">
        {/* 文件图标 */}
        <div 
          className="h-10 w-10 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: `${fileColor}15`, color: fileColor }}
        >
          {getFileIcon(fileType)}
        </div>
        
        {/* 文件信息 */}
        <div className="flex-1 min-w-0">
          <h4 
            className={cn(
              "text-sm font-medium truncate mb-1 transition-colors",
              isHovered ? "text-blue-600 dark:text-blue-400" : "text-slate-800 dark:text-slate-200"
            )}
            title={doc.source}
          >
            {doc.source}
          </h4>
          <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
            <span 
              className="px-2 py-0.5 rounded"
              style={{ backgroundColor: `${fileColor}15`, color: fileColor }}
            >
              {doc.file_type?.toUpperCase() || 'OTHER'}
            </span>
            <span>{doc.chunks} 片段</span>
            <span>{doc.date ? new Date(doc.date).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }) : "—"}</span>
          </div>
        </div>
        
        {/* 操作按钮 */}
        <div 
          className={cn(
            "flex items-center gap-1 transition-opacity duration-200",
            isHovered ? "opacity-100" : "opacity-0"
          )}
        >
          <button
            onClick={(e) => { e.stopPropagation(); onView() }}
            className="p-2 rounded-lg transition-colors text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
            title="预览"
          >
            <Eye className="h-4 w-4" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete() }}
            disabled={isDeleting}
            className={cn(
              "p-2 rounded-lg transition-colors hover:bg-red-50 dark:hover:bg-red-900/30",
              isDeleting ? "text-slate-400 dark:text-slate-500" : "text-red-500 dark:text-red-400"
            )}
            title="删除"
          >
            {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </motion.div>
  )
}

// 集合卡片组件
interface CollectionCardProps {
  collection: Collection
  isSelected: boolean
  onSelect: () => void
  onRename: () => void
  onDelete: () => void
  isDeleting: boolean
}

const CollectionCard: React.FC<CollectionCardProps> = ({ collection, isSelected, onSelect, onRename, onDelete, isDeleting }) => {
  const [isHovered, setIsHovered] = useState(false)
  
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      onClick={onSelect}
      className={cn(
        "rounded-lg p-3 transition-all duration-300 cursor-pointer",
        isHovered ? "shadow-lg dark:shadow-slate-900/50" : "shadow-sm dark:shadow-slate-900/30",
        isSelected 
          ? "bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-500 dark:border-blue-400" 
          : "bg-white dark:bg-slate-800 border-2 border-transparent"
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <div 
            className={cn(
              "h-8 w-8 rounded-lg flex items-center justify-center shrink-0",
              isSelected ? "bg-blue-100 dark:bg-blue-800/50" : "bg-blue-50 dark:bg-blue-900/30"
            )}
          >
            <Database className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium truncate text-slate-800 dark:text-slate-200" title={collection.name}>
                {collection.name}
              </p>
              {isSelected && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-blue-600 dark:bg-blue-500 text-white">
                  上传目标
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">{collection.count} 个片段</p>
          </div>
        </div>
        <div 
          className={cn(
            "flex items-center gap-0.5 transition-opacity duration-200",
            isHovered ? "opacity-100" : "opacity-0"
          )}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={onRename}
            className="p-1.5 rounded-lg transition-colors text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
            title="重命名"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={onDelete}
            disabled={isDeleting}
            className={cn(
              "p-1.5 rounded-lg transition-colors hover:bg-red-50 dark:hover:bg-red-900/30",
              isDeleting ? "text-slate-400 dark:text-slate-500" : "text-red-500 dark:text-red-400"
            )}
            title="删除集合"
          >
            {isDeleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>
    </motion.div>
  )
}

// 空状态组件
interface EmptyStateProps {
  type: 'literature' | 'collection'
  onAction?: () => void
}

const EmptyState: React.FC<EmptyStateProps> = ({ type, onAction }) => {
  const config = {
    literature: {
      icon: <FileText className="h-12 w-12" />,
      title: "暂无文献",
      description: "点击右上角「上传文献」按钮，开始管理你的科研文献",
      action: "上传文献",
    },
    collection: {
      icon: <FolderOpen className="h-10 w-10" />,
      title: "暂无集合",
      description: "知识库集合为空",
      action: null,
    }
  }
  
  const { icon, title, description, action } = config[type]
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="flex flex-col items-center justify-center py-12 px-4"
    >
      <div className="mb-4 p-4 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">
        {icon}
      </div>
      <h4 className="text-base font-medium mb-2 text-slate-800 dark:text-slate-200">{title}</h4>
      <p className="text-sm text-center mb-4 max-w-xs text-slate-500 dark:text-slate-400">{description}</p>
      {action && onAction && (
        <button
          onClick={onAction}
          className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 transition-all duration-200 hover:scale-[0.98]"
        >
          {action}
        </button>
      )}
    </motion.div>
  )
}

// 确认弹窗组件
interface ConfirmModalProps {
  isOpen: boolean
  title: string
  message: string
  onConfirm: () => void
  onCancel: () => void
  isLoading?: boolean
}

const ConfirmModal: React.FC<ConfirmModalProps> = ({ isOpen, title, message, onConfirm, onCancel, isLoading }) => (
  <AnimatePresence>
    {isOpen && (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
        onClick={onCancel}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-sm mx-4 shadow-2xl dark:shadow-slate-900/50"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="h-10 w-10 rounded-full flex items-center justify-center bg-red-50 dark:bg-red-900/30">
              <AlertCircle className="h-5 w-5 text-red-500 dark:text-red-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-200">{title}</h3>
          </div>
          <p className="text-sm mb-6 text-slate-600 dark:text-slate-400">{message}</p>
          <div className="flex gap-3 justify-end">
            <button
              onClick={onCancel}
              disabled={isLoading}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600"
            >
              取消
            </button>
            <button
              onClick={onConfirm}
              disabled={isLoading}
              className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700 transition-all duration-200 hover:scale-[0.98] flex items-center gap-2"
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              确认删除
            </button>
          </div>
        </motion.div>
      </motion.div>
    )}
  </AnimatePresence>
)

// 输入弹窗组件（用于创建/重命名）
interface InputModalProps {
  isOpen: boolean
  title: string
  placeholder: string
  defaultValue?: string
  confirmText: string
  onConfirm: (value: string) => void
  onCancel: () => void
  isLoading?: boolean
}

const InputModal: React.FC<InputModalProps> = ({ 
  isOpen, title, placeholder, defaultValue = "", confirmText, onConfirm, onCancel, isLoading 
}) => {
  const [value, setValue] = useState(defaultValue)
  
  useEffect(() => {
    if (isOpen) {
      setValue(defaultValue)
    }
  }, [isOpen, defaultValue])
  
  const handleConfirm = () => {
    if (value.trim()) {
      onConfirm(value.trim())
    }
  }
  
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={onCancel}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            onClick={(e) => e.stopPropagation()}
            className="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-sm mx-4 shadow-2xl dark:shadow-slate-900/50"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="h-10 w-10 rounded-full flex items-center justify-center bg-blue-50 dark:bg-blue-900/30">
                <Database className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-200">{title}</h3>
            </div>
            
            <input
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={placeholder}
              className="w-full px-4 py-3 rounded-lg border text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500"
              onKeyDown={(e) => e.key === 'Enter' && handleConfirm()}
              autoFocus
            />
            
            <p className="text-xs mb-4 text-slate-500 dark:text-slate-400">
              名称只能包含字母、数字、下划线和中划线
            </p>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={onCancel}
                disabled={isLoading}
                className="px-4 py-2 rounded-lg text-sm font-medium transition-colors text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600"
              >
                取消
              </button>
              <button
                onClick={handleConfirm}
                disabled={isLoading || !value.trim()}
                className="px-4 py-2 rounded-lg text-sm font-medium text-white transition-all duration-200 hover:scale-[0.98] flex items-center gap-2 disabled:opacity-50 bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
              >
                {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                {confirmText}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

// Toast 提示组件
interface ToastProps {
  message: string
  type: 'success' | 'error'
  isVisible: boolean
}

const Toast: React.FC<ToastProps> = ({ message, type, isVisible }) => (
  <AnimatePresence>
    {isVisible && (
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className={cn(
          "fixed top-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-lg text-white text-sm font-medium shadow-lg",
          type === 'success' ? "bg-green-500 dark:bg-green-600" : "bg-red-500 dark:bg-red-600"
        )}
      >
        {type === 'success' ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
        {message}
      </motion.div>
    )}
  </AnimatePresence>
)

// 全屏进度遮罩组件
interface ProgressOverlayProps {
  isVisible: boolean
  title: string
  message: string
  progress?: number // 0-100，如果不传则显示无限加载动画
}

const ProgressOverlay: React.FC<ProgressOverlayProps> = ({ isVisible, title, message, progress }) => (
  <AnimatePresence>
    {isVisible && (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="bg-white dark:bg-slate-800 rounded-xl p-8 w-full max-w-sm mx-4 text-center shadow-2xl dark:shadow-slate-900/50"
        >
          {/* 加载动画 */}
          <div className="relative w-20 h-20 mx-auto mb-6">
            {progress !== undefined ? (
              // 有进度的圆环
              <svg className="w-20 h-20 transform -rotate-90">
                <circle
                  cx="40"
                  cy="40"
                  r="36"
                  className="stroke-slate-200 dark:stroke-slate-600"
                  strokeWidth="6"
                  fill="none"
                />
                <motion.circle
                  cx="40"
                  cy="40"
                  r="36"
                  className="stroke-blue-600 dark:stroke-blue-400"
                  strokeWidth="6"
                  fill="none"
                  strokeLinecap="round"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: progress / 100 }}
                  transition={{ duration: 0.3 }}
                  style={{ strokeDasharray: "226.19", strokeDashoffset: "0" }}
                />
              </svg>
            ) : (
              // 无限旋转动画
              <svg className="w-20 h-20 animate-spin" viewBox="0 0 80 80">
                <circle
                  cx="40"
                  cy="40"
                  r="36"
                  className="stroke-slate-200 dark:stroke-slate-600"
                  strokeWidth="6"
                  fill="none"
                />
                <circle
                  cx="40"
                  cy="40"
                  r="36"
                  className="stroke-blue-600 dark:stroke-blue-400"
                  strokeWidth="6"
                  fill="none"
                  strokeLinecap="round"
                  strokeDasharray="80 150"
                />
              </svg>
            )}
            {progress !== undefined && (
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-lg font-bold text-blue-600 dark:text-blue-400">{Math.round(progress)}%</span>
              </div>
            )}
          </div>
          
          <h3 className="text-lg font-semibold mb-2 text-slate-800 dark:text-slate-200">{title}</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">{message}</p>
        </motion.div>
      </motion.div>
    )}
  </AnimatePresence>
)


// 图片数据类型
interface DocumentImage {
  base64: string
  width: number
  height: number
  page: number
  index: number
}

// 图片查看器组件
interface ImageViewerProps {
  image: DocumentImage | null
  isOpen: boolean
  onClose: () => void
  onPrev: () => void
  onNext: () => void
  currentIndex: number
  totalCount: number
}

const ImageViewer: React.FC<ImageViewerProps> = ({ 
  image, isOpen, onClose, onPrev, onNext, currentIndex, totalCount 
}) => (
  <AnimatePresence>
    {isOpen && image && (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="relative max-w-[90vw] max-h-[90vh]"
          onClick={(e) => e.stopPropagation()}
        >
          <img 
            src={image.base64} 
            alt={`图片 ${currentIndex + 1}`}
            className="max-w-full max-h-[85vh] object-contain rounded-lg"
          />
          
          {/* 图片信息 */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/60 text-white px-4 py-2 rounded-lg text-sm">
            第 {image.page} 页 · {currentIndex + 1} / {totalCount} · {image.width} × {image.height}
          </div>
          
          {/* 关闭按钮 */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 bg-black/60 text-white rounded-full hover:bg-black/80 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
          
          {/* 上一张 */}
          {currentIndex > 0 && (
            <button
              onClick={(e) => { e.stopPropagation(); onPrev() }}
              className="absolute left-4 top-1/2 -translate-y-1/2 p-3 bg-black/60 text-white rounded-full hover:bg-black/80 transition-colors"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          )}
          
          {/* 下一张 */}
          {currentIndex < totalCount - 1 && (
            <button
              onClick={(e) => { e.stopPropagation(); onNext() }}
              className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-black/60 text-white rounded-full hover:bg-black/80 transition-colors"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </motion.div>
      </motion.div>
    )}
  </AnimatePresence>
)

// 文献内容查看/编辑弹窗
interface DocumentViewModalProps {
  isOpen: boolean
  doc: Document | null
  content: string
  images: DocumentImage[]
  isLoading: boolean
  isEditing: boolean
  isSaving: boolean
  editedContent: string
  onClose: () => void
  onEdit: () => void
  onSave: () => void
  onCancelEdit: () => void
  onContentChange: (content: string) => void
}

const DocumentViewModal: React.FC<DocumentViewModalProps> = ({
  isOpen, doc, content, images, isLoading, isEditing, isSaving, editedContent,
  onClose, onEdit, onSave, onCancelEdit, onContentChange
}) => {
  const [activeTab, setActiveTab] = useState<'text' | 'images'>('text')
  const [viewerOpen, setViewerOpen] = useState(false)
  const [viewerIndex, setViewerIndex] = useState(0)
  
  // 重置标签页当弹窗打开时
  useEffect(() => {
    if (isOpen) {
      setActiveTab('text')
      setViewerOpen(false)
    }
  }, [isOpen])
  
  const openImageViewer = (index: number) => {
    setViewerIndex(index)
    setViewerOpen(true)
  }
  
  const hasImages = images && images.length > 0
  
  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
            onClick={onClose}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white dark:bg-slate-800 rounded-xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden shadow-2xl dark:shadow-slate-900/50"
            >
              {/* 头部 */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="h-10 w-10 rounded-lg flex items-center justify-center bg-blue-50 dark:bg-blue-900/30">
                    <FileText className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-lg font-semibold truncate text-slate-800 dark:text-slate-200">{doc?.source || "文献内容"}</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {doc?.chunks} 个片段 · {doc?.collection || "默认集合"}
                      {hasImages && ` · ${images.length} 张图片`}
                    </p>
                  </div>
                </div>
                <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
                  <X className="h-5 w-5 text-slate-500 dark:text-slate-400" />
                </button>
              </div>
              
              {/* 标签页切换（仅当有图片时显示） */}
              {hasImages && !isEditing && (
                <div className="flex items-center gap-1 px-6 pt-4">
                  <button
                    onClick={() => setActiveTab('text')}
                    className={cn(
                      "px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                      activeTab === 'text' 
                        ? "text-white bg-blue-600 dark:bg-blue-500" 
                        : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      文本内容
                    </span>
                  </button>
                  <button
                    onClick={() => setActiveTab('images')}
                    className={cn(
                      "px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                      activeTab === 'images' 
                        ? "text-white bg-blue-600 dark:bg-blue-500" 
                        : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      图片 ({images.length})
                    </span>
                  </button>
                </div>
              )}
              
              {/* 内容区 */}
              <div className="flex-1 overflow-hidden p-6">
                {isLoading ? (
                  <div className="flex items-center justify-center h-64">
                    <Loader2 className="h-8 w-8 animate-spin text-blue-600 dark:text-blue-400" />
                  </div>
                ) : isEditing ? (
                  <textarea
                    value={editedContent}
                    onChange={(e) => onContentChange(e.target.value)}
                    className="w-full h-[50vh] p-4 rounded-lg border text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200"
                    placeholder="输入文献内容..."
                  />
                ) : activeTab === 'text' ? (
                  <div className="h-[50vh] overflow-auto p-4 rounded-lg bg-slate-50 dark:bg-slate-900/50">
                    <pre className="whitespace-pre-wrap text-sm leading-relaxed font-sans text-slate-700 dark:text-slate-300">
                      {content}
                    </pre>
                  </div>
                ) : (
                  /* 图片画廊 */
                  <div className="h-[50vh] overflow-auto">
                    {images.length === 0 ? (
                      <div className="flex flex-col items-center justify-center h-full text-slate-500 dark:text-slate-400">
                        <svg className="h-16 w-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        <p className="text-sm">该文献暂无图片</p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                        {images.map((img, index) => (
                          <motion.div
                            key={`${img.page}-${img.index}`}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: index * 0.05 }}
                            className="relative group cursor-pointer rounded-lg overflow-hidden shadow-sm dark:shadow-slate-900/30"
                            onClick={() => openImageViewer(index)}
                          >
                            <div className="aspect-[4/3] bg-slate-100 dark:bg-slate-700">
                              <img 
                                src={img.base64} 
                                alt={`第 ${img.page} 页 - 图片 ${img.index + 1}`}
                                className="w-full h-full object-contain"
                              />
                            </div>
                            {/* 悬浮遮罩 */}
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center">
                              <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                                <Eye className="h-8 w-8 text-white" />
                              </div>
                            </div>
                            {/* 图片信息 */}
                            <div className="absolute bottom-0 left-0 right-0 px-2 py-1.5 text-xs bg-black/60 text-white">
                              第 {img.page} 页 · {img.width}×{img.height}
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              {/* 底部操作 */}
              <div className="flex justify-end gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-700">
                {isEditing ? (
                  <>
                    <button
                      onClick={onCancelEdit}
                      disabled={isSaving}
                      className="px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600"
                    >
                      <X className="h-4 w-4" /> 取消
                    </button>
                    <button
                      onClick={onSave}
                      disabled={isSaving || !editedContent.trim()}
                      className="px-4 py-2 rounded-lg text-sm font-medium text-white transition-all duration-200 hover:scale-[0.98] flex items-center gap-2 bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
                    >
                      {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                      保存
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={onClose}
                      className="px-4 py-2 rounded-lg text-sm font-medium transition-colors text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600"
                    >
                      关闭
                    </button>
                    <button
                      onClick={onEdit}
                      disabled={isLoading}
                      className="px-4 py-2 rounded-lg text-sm font-medium text-white transition-all duration-200 hover:scale-[0.98] flex items-center gap-2 bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
                    >
                      <Edit className="h-4 w-4" /> 编辑
                    </button>
                  </>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* 图片查看器 */}
      <ImageViewer
        image={images[viewerIndex] || null}
        isOpen={viewerOpen}
        onClose={() => setViewerOpen(false)}
        onPrev={() => setViewerIndex(i => Math.max(0, i - 1))}
        onNext={() => setViewerIndex(i => Math.min(images.length - 1, i + 1))}
        currentIndex={viewerIndex}
        totalCount={images.length}
      />
    </>
  )
}

// ==================== 主组件 ====================

export default function DocumentsPage() {
  // 数据状态
  const [documents, setDocuments] = useState<Document[]>([])
  const [collections, setCollections] = useState<Collection[]>([])
  const [fileTypeStats, setFileTypeStats] = useState<FileTypeStat[]>([])
  const [selectedFileType, setSelectedFileType] = useState<string | null>(null)
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null) // 当前选中的知识库
  
  // 加载状态
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [isRebuilding, setIsRebuilding] = useState(false)
  const [deletingDoc, setDeletingDoc] = useState<string | null>(null)
  const [deletingCollection, setDeletingCollection] = useState<string | null>(null)
  
  // 弹窗状态
  const [viewModalOpen, setViewModalOpen] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
  const [docContent, setDocContent] = useState("")
  const [docImages, setDocImages] = useState<DocumentImage[]>([])
  const [editedContent, setEditedContent] = useState("")
  const [isLoadingContent, setIsLoadingContent] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  
  // 确认弹窗状态
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean
    title: string
    message: string
    onConfirm: () => void
  }>({ isOpen: false, title: "", message: "", onConfirm: () => {} })
  
  // 输入弹窗状态（创建/重命名）
  const [inputModal, setInputModal] = useState<{
    isOpen: boolean
    title: string
    placeholder: string
    defaultValue: string
    confirmText: string
    onConfirm: (value: string) => void
    isLoading: boolean
  }>({ 
    isOpen: false, 
    title: "", 
    placeholder: "", 
    defaultValue: "", 
    confirmText: "", 
    onConfirm: () => {}, 
    isLoading: false 
  })
  
  // Toast 状态
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error'; isVisible: boolean }>({
    message: "", type: "success", isVisible: false
  })
  
  // 进度遮罩状态
  const [progressOverlay, setProgressOverlay] = useState<{
    isVisible: boolean
    title: string
    message: string
    progress?: number
  }>({ isVisible: false, title: "", message: "", progress: undefined })

  // 显示 Toast
  const showToast = useCallback((message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type, isVisible: true })
    setTimeout(() => setToast(prev => ({ ...prev, isVisible: false })), 3000)
  }, [])

  // 模拟进度动画 hook
  const useSimulatedProgress = () => {
    const intervalRef = React.useRef<NodeJS.Timeout | null>(null)
    const progressRef = React.useRef(0)
    
    const startProgress = useCallback((
      title: string, 
      message: string
    ) => {
      progressRef.current = 0
      setProgressOverlay({
        isVisible: true,
        title,
        message,
        progress: 0
      })
      
      // 模拟进度：快速到 30%，然后慢慢到 70%，最后等待完成
      intervalRef.current = setInterval(() => {
        progressRef.current += Math.random() * 8 + 2 // 每次增加 2-10%
        
        if (progressRef.current >= 70) {
          // 到达 70% 后放慢速度
          progressRef.current = Math.min(progressRef.current, 85)
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = setInterval(() => {
              progressRef.current += Math.random() * 2 + 0.5 // 每次增加 0.5-2.5%
              if (progressRef.current >= 90) {
                progressRef.current = 90 // 最多到 90%，等待真正完成
                if (intervalRef.current) clearInterval(intervalRef.current)
              }
              setProgressOverlay(prev => ({ ...prev, progress: Math.round(progressRef.current) }))
            }, 200)
          }
        }
        
        setProgressOverlay(prev => ({ ...prev, progress: Math.round(progressRef.current) }))
      }, 100)
    }, [])
    
    const updateMessage = useCallback((message: string) => {
      setProgressOverlay(prev => ({ ...prev, message }))
    }, [])
    
    const completeProgress = useCallback(async () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      
      // 平滑完成到 100%
      const currentProgress = progressRef.current
      const steps = 10
      const increment = (100 - currentProgress) / steps
      
      for (let i = 0; i < steps; i++) {
        progressRef.current = Math.min(currentProgress + increment * (i + 1), 100)
        setProgressOverlay(prev => ({ ...prev, progress: Math.round(progressRef.current) }))
        await new Promise(resolve => setTimeout(resolve, 30))
      }
      
      // 短暂显示 100% 后关闭
      await new Promise(resolve => setTimeout(resolve, 300))
      setProgressOverlay(prev => ({ ...prev, isVisible: false }))
      progressRef.current = 0
    }, [])
    
    const cancelProgress = useCallback(() => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      setProgressOverlay(prev => ({ ...prev, isVisible: false }))
      progressRef.current = 0
    }, [])
    
    return { startProgress, updateMessage, completeProgress, cancelProgress }
  }
  
  const { startProgress, updateMessage, completeProgress, cancelProgress } = useSimulatedProgress()

  // 数据获取
  const fetchDocuments = async (fileType?: string | null) => {
    setIsLoading(true)
    try {
      const data = await chatService.getDocuments(fileType || undefined)
      setDocuments(data.documents || [])
    } catch (error) {
      console.error('获取文档列表失败:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchCollections = async () => {
    try {
      const data = await chatService.getCollections()
      setCollections(data.collections || [])
    } catch (error) {
      console.error('获取集合列表失败:', error)
    }
  }

  const fetchFileTypeStats = async () => {
    try {
      const data = await chatService.getFileTypeStats()
      setFileTypeStats(data.stats || [])
    } catch (error) {
      console.error('获取文件类型统计失败:', error)
    }
  }

  useEffect(() => {
    fetchDocuments()
    fetchCollections()
    fetchFileTypeStats()
  }, [])

  // 文件类型筛选
  const handleFileTypeChange = (type: string | null) => {
    setSelectedFileType(type)
    fetchDocuments(type)
  }

  // 文件上传
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    const targetCollection = selectedCollection || undefined
    startProgress(
      "正在上传文献",
      `正在处理 ${file.name}${targetCollection ? ` → ${targetCollection}` : ''}...`
    )
    
    try {
      const result = await chatService.uploadDocument(file, targetCollection)
      updateMessage("正在更新索引...")
      await Promise.all([fetchDocuments(selectedFileType), fetchCollections(), fetchFileTypeStats()])
      await completeProgress()
      showToast(`上传成功！${result.message || ''}`, 'success')
    } catch (error: any) {
      cancelProgress()
      showToast(`上传失败: ${error.response?.data?.detail || error.message}`, 'error')
    } finally {
      setIsUploading(false)
      e.target.value = ""
    }
  }

  // 重建索引
  const handleRebuildIndex = async () => {
    setIsRebuilding(true)
    startProgress("正在重建索引", "正在扫描文献目录...")
    
    try {
      const result = await chatService.rebuildIndex()
      updateMessage("正在更新数据...")
      await Promise.all([fetchDocuments(selectedFileType), fetchCollections(), fetchFileTypeStats()])
      await completeProgress()
      
      // 根据结果显示不同的提示
      if (result.num_documents === 0 && result.num_chunks === 0) {
        showToast("目录中暂无新文献，已上传的文献不受影响", 'success')
      } else {
        showToast(`索引重建成功！新增 ${result.num_documents || 0} 篇文献，${result.num_chunks || 0} 个片段`, 'success')
      }
    } catch (error: any) {
      cancelProgress()
      showToast(`索引重建失败: ${error.response?.data?.detail || error.message}`, 'error')
    } finally {
      setIsRebuilding(false)
    }
  }

  // 删除文献
  const handleDeleteDocument = (source: string, collection?: string) => {
    setConfirmModal({
      isOpen: true,
      title: "删除文献",
      message: `确定要删除「${source}」吗？此操作不可恢复。`,
      onConfirm: async () => {
        setDeletingDoc(source)
        setConfirmModal(prev => ({ ...prev, isOpen: false }))
        startProgress("正在删除文献", `正在删除 ${source}...`)
        
        try {
          await chatService.deleteDocumentBySource(source, collection)
          updateMessage("正在更新列表...")
          await Promise.all([fetchDocuments(selectedFileType), fetchCollections(), fetchFileTypeStats()])
          await completeProgress()
          showToast("文献删除成功", 'success')
        } catch (error: any) {
          cancelProgress()
          showToast(`删除失败: ${error.response?.data?.detail || error.message}`, 'error')
        } finally {
          setDeletingDoc(null)
        }
      }
    })
  }

  // 删除集合
  const handleDeleteCollection = (name: string) => {
    setConfirmModal({
      isOpen: true,
      title: "删除知识库",
      message: `确定要删除知识库「${name}」吗？此操作将删除该集合下的所有数据。`,
      onConfirm: async () => {
        setDeletingCollection(name)
        setConfirmModal(prev => ({ ...prev, isOpen: false }))
        startProgress("正在删除知识库", `正在删除 ${name}...`)
        
        try {
          await chatService.deleteCollection(name)
          updateMessage("正在更新列表...")
          await Promise.all([fetchDocuments(selectedFileType), fetchCollections(), fetchFileTypeStats()])
          await completeProgress()
          showToast("知识库删除成功", 'success')
        } catch (error: any) {
          cancelProgress()
          showToast(`删除失败: ${error.response?.data?.detail || error.message}`, 'error')
        } finally {
          setDeletingCollection(null)
        }
      }
    })
  }

  // 创建知识库
  const handleCreateCollection = () => {
    setInputModal({
      isOpen: true,
      title: "创建知识库",
      placeholder: "请输入知识库名称",
      defaultValue: "",
      confirmText: "创建",
      isLoading: false,
      onConfirm: async (name: string) => {
        setInputModal(prev => ({ ...prev, isLoading: true }))
        startProgress("正在创建知识库", `正在创建 ${name}...`)
        
        try {
          await chatService.createCollection(name)
          updateMessage("正在更新列表...")
          await fetchCollections()
          await completeProgress()
          showToast(`知识库「${name}」创建成功`, 'success')
          setInputModal(prev => ({ ...prev, isOpen: false }))
        } catch (error: any) {
          cancelProgress()
          showToast(`创建失败: ${error.response?.data?.detail || error.message}`, 'error')
        } finally {
          setInputModal(prev => ({ ...prev, isLoading: false }))
        }
      }
    })
  }

  // 重命名知识库
  const handleRenameCollection = (oldName: string) => {
    setInputModal({
      isOpen: true,
      title: "重命名知识库",
      placeholder: "请输入新名称",
      defaultValue: oldName,
      confirmText: "确认",
      isLoading: false,
      onConfirm: async (newName: string) => {
        if (newName === oldName) {
          setInputModal(prev => ({ ...prev, isOpen: false }))
          return
        }
        
        setInputModal(prev => ({ ...prev, isLoading: true }))
        startProgress("正在重命名知识库", `正在将 ${oldName} 重命名为 ${newName}...`)
        
        try {
          await chatService.renameCollection(oldName, newName)
          updateMessage("正在更新列表...")
          await Promise.all([fetchDocuments(selectedFileType), fetchCollections(), fetchFileTypeStats()])
          await completeProgress()
          showToast(`知识库已重命名为「${newName}」`, 'success')
          setInputModal(prev => ({ ...prev, isOpen: false }))
        } catch (error: any) {
          cancelProgress()
          showToast(`重命名失败: ${error.response?.data?.detail || error.message}`, 'error')
        } finally {
          setInputModal(prev => ({ ...prev, isLoading: false }))
        }
      }
    })
  }

  // 查看文献
  const handleViewDocument = async (doc: Document) => {
    setSelectedDoc(doc)
    setViewModalOpen(true)
    setIsLoadingContent(true)
    setIsEditing(false)
    setDocImages([])
    
    try {
      const data = await chatService.getDocumentContent(doc.source, doc.collection)
      setDocContent(data.content)
      setEditedContent(data.content)
      // 设置图片数据
      if (data.images && data.images.length > 0) {
        setDocImages(data.images)
      }
    } catch (error: any) {
      setDocContent(`获取内容失败: ${error.response?.data?.detail || error.message}`)
      setEditedContent("")
      setDocImages([])
    } finally {
      setIsLoadingContent(false)
    }
  }

  // 保存编辑
  const handleSaveContent = async () => {
    if (!selectedDoc || !editedContent.trim()) return
    
    setIsSaving(true)
    try {
      await chatService.updateDocumentContent(selectedDoc.source, editedContent, selectedDoc.collection)
      setDocContent(editedContent)
      setIsEditing(false)
      await Promise.all([fetchDocuments(selectedFileType), fetchCollections()])
      showToast("文献内容更新成功", 'success')
    } catch (error: any) {
      showToast(`保存失败: ${error.response?.data?.detail || error.message}`, 'error')
    } finally {
      setIsSaving(false)
    }
  }

  // 统计数据
  const totalFiles = fileTypeStats.reduce((acc, stat) => acc + stat.count, 0)
  const totalChunks = collections.reduce((acc, c) => acc + c.count, 0)
  const activeFileTypes = fileTypeStats.filter(stat => stat.count > 0)

  // 文件上传按钮引用
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  return (
    <div className="h-full overflow-auto bg-slate-50 dark:bg-slate-900">
      <div className="max-w-7xl mx-auto p-6">
        {/* 页面标题 */}
        <div className="mb-6">
          <h1 className="text-xl font-bold mb-1 text-slate-800 dark:text-slate-200">文献管理</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">管理知识库文献，支持 PDF、Word、Markdown、TXT 等格式</p>
        </div>

        {/* 统计卡片区 */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard title="总文献数" value={totalFiles} icon={<FolderOpen className="h-5 w-5" />} color={colors.primary} />
          <StatCard title="总片段数" value={totalChunks} icon={<FileText className="h-5 w-5" />} color="#00B42A" />
          <StatCard title="知识库数" value={collections.length} icon={<Database className="h-5 w-5" />} color="#722ED1" />
          <StatCard title="文件类型" value={activeFileTypes.length} icon={<Files className="h-5 w-5" />} color="#FF7D00" />
        </div>

        {/* 文件类型筛选 */}
        <div className="flex flex-wrap items-center gap-2 mb-6">
          <span className="text-sm mr-2 text-slate-500 dark:text-slate-400">筛选:</span>
          <button
            onClick={() => handleFileTypeChange(null)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200",
              selectedFileType === null 
                ? "text-white bg-blue-600 dark:bg-blue-500" 
                : "text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-800"
            )}
          >
            全部 ({totalFiles})
          </button>
          {activeFileTypes.map((stat) => (
            <button
              key={stat.type}
              onClick={() => handleFileTypeChange(stat.type)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200",
                selectedFileType === stat.type 
                  ? "text-white bg-blue-600 dark:bg-blue-500" 
                  : "text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-800"
              )}
            >
              {stat.label} ({stat.count})
            </button>
          ))}
        </div>

        {/* 主内容区：文献列表 + 知识库集合 */}
        <div className="grid lg:grid-cols-10 gap-6">
          {/* 文献展示区 (7/10) */}
          <div className="lg:col-span-7">
            <div className="bg-white dark:bg-slate-800 rounded-lg shadow-sm dark:shadow-slate-900/30">
              {/* 标题栏 */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
                <div>
                  <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">
                    {selectedFileType ? `${fileTypeStats.find(s => s.type === selectedFileType)?.label || ''} 文件` : '全部文献'}
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400">{documents.length} 个文件</p>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    onChange={handleFileUpload}
                    accept=".txt,.md,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
                    disabled={isUploading}
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white transition-all duration-200 hover:scale-[0.98] active:scale-[0.96] bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
                    title={selectedCollection ? `上传到「${selectedCollection}」` : '上传到默认知识库'}
                  >
                    {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                    上传文献
                    {selectedCollection && (
                      <span className="text-xs opacity-80">→ {selectedCollection}</span>
                    )}
                  </button>
                </div>
              </div>
              
              {/* 文献列表 */}
              <div className="p-4 max-h-[520px] overflow-auto">
                {isLoading ? (
                  <div className="flex items-center justify-center py-16">
                    <Loader2 className="h-8 w-8 animate-spin text-blue-600 dark:text-blue-400" />
                  </div>
                ) : documents.length === 0 ? (
                  <EmptyState type="literature" onAction={() => fileInputRef.current?.click()} />
                ) : (
                  <div className="space-y-3">
                    <AnimatePresence>
                      {documents.map((doc) => (
                        <LiteratureCard
                          key={`${doc.collection}::${doc.source}`}
                          doc={doc}
                          onView={() => handleViewDocument(doc)}
                          onDelete={() => handleDeleteDocument(doc.source, doc.collection)}
                          isDeleting={deletingDoc === doc.source}
                        />
                      ))}
                    </AnimatePresence>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 右侧面板 (3/10) */}
          <div className="lg:col-span-3 space-y-6">
            {/* 知识库集合区 */}
            <div className="bg-white dark:bg-slate-800 rounded-lg shadow-sm dark:shadow-slate-900/30">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
                <div>
                  <h2 className="text-base font-semibold flex items-center gap-2 text-slate-800 dark:text-slate-200">
                    <Database className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    知识库集合
                  </h2>
                  {selectedCollection && (
                    <p className="text-xs mt-0.5 text-blue-600 dark:text-blue-400">
                      点击其他集合切换，或点击已选集合取消
                    </p>
                  )}
                </div>
                <button
                  onClick={handleCreateCollection}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 hover:scale-[0.98] bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                >
                  <Plus className="h-3.5 w-3.5" />
                  新建
                </button>
              </div>
              <div className="p-4 max-h-[280px] overflow-auto">
                {collections.length === 0 ? (
                  <EmptyState type="collection" />
                ) : (
                  <div className="space-y-2">
                    <AnimatePresence>
                      {collections.map((coll) => (
                        <CollectionCard
                          key={coll.name}
                          collection={coll}
                          isSelected={selectedCollection === coll.name}
                          onSelect={() => setSelectedCollection(prev => prev === coll.name ? null : coll.name)}
                          onRename={() => handleRenameCollection(coll.name)}
                          onDelete={() => handleDeleteCollection(coll.name)}
                          isDeleting={deletingCollection === coll.name}
                        />
                      ))}
                    </AnimatePresence>
                  </div>
                )}
              </div>
            </div>

            {/* 索引操作区 */}
            <div className="bg-white dark:bg-slate-800 rounded-lg p-4 shadow-sm dark:shadow-slate-900/30">
              <h2 className="text-base font-semibold mb-3 flex items-center gap-2 text-slate-800 dark:text-slate-200">
                <RefreshCw className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                批量导入
              </h2>
              <button
                onClick={handleRebuildIndex}
                disabled={isRebuilding}
                className={cn(
                  "w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 hover:scale-[0.98] active:scale-[0.96]",
                  "bg-slate-100 dark:bg-slate-700",
                  isRebuilding ? "text-slate-400 dark:text-slate-500" : "text-slate-600 dark:text-slate-300"
                )}
              >
                {isRebuilding ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    扫描中...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4" />
                    扫描目录
                  </>
                )}
              </button>
              <p className="text-xs mt-2 text-center text-slate-500 dark:text-slate-400">
                扫描 data/documents 目录导入文献
              </p>
              <p className="text-xs text-center text-slate-500 dark:text-slate-400">
                （已上传的文献不受影响）
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 弹窗组件 */}
      <DocumentViewModal
        isOpen={viewModalOpen}
        doc={selectedDoc}
        content={docContent}
        images={docImages}
        isLoading={isLoadingContent}
        isEditing={isEditing}
        isSaving={isSaving}
        editedContent={editedContent}
        onClose={() => setViewModalOpen(false)}
        onEdit={() => setIsEditing(true)}
        onSave={handleSaveContent}
        onCancelEdit={() => { setEditedContent(docContent); setIsEditing(false) }}
        onContentChange={setEditedContent}
      />

      <ConfirmModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal(prev => ({ ...prev, isOpen: false }))}
      />

      <InputModal
        isOpen={inputModal.isOpen}
        title={inputModal.title}
        placeholder={inputModal.placeholder}
        defaultValue={inputModal.defaultValue}
        confirmText={inputModal.confirmText}
        onConfirm={inputModal.onConfirm}
        onCancel={() => setInputModal(prev => ({ ...prev, isOpen: false }))}
        isLoading={inputModal.isLoading}
      />

      <Toast message={toast.message} type={toast.type} isVisible={toast.isVisible} />
      
      <ProgressOverlay
        isVisible={progressOverlay.isVisible}
        title={progressOverlay.title}
        message={progressOverlay.message}
        progress={progressOverlay.progress}
      />
    </div>
  )
}
