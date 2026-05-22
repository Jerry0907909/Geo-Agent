import React, { useState, useEffect, useCallback } from "react"
import { useI18nStore } from "@/i18n"
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
  primary: "#3964FE",
  primaryHover: "#2D55F1",
  danger: "#F53F3F",
  dangerHover: "#CB2E2E",
  bgLight: "#F8FAFD",
  bgCard: "#FFFFFF",
  border: "#E6EAF2",
  textTitle: "#0F1115",
  textBody: "#424750",
  textMuted: "#81858C",
  shadow: "rgba(72, 104, 178, 0.04) 0px -2px 2px 0px, rgba(106, 111, 117, 0.09) 0px 2px 2px 0px, rgba(72, 104, 178, 0.08) 0px 1px 2px 0px",
  shadowHover: "rgba(0, 0, 0, 0.02) 0px 4px 12px 0px, rgba(72, 104, 178, 0.01) 0px 2px 2px 0px, rgba(72, 104, 178, 0.03) 0px 30px 60px 0px",
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
    whileHover={{ y: -1 }}
    transition={{ duration: 0.2 }}
    className="shadow-ds-surface rounded-[24px] border border-border/80 bg-white p-4 dark:bg-card"
  >
    <div className="flex items-center justify-between">
      <div>
        <p className="mb-1 text-xs text-muted-foreground">{title}</p>
        <p className="text-xl font-semibold text-foreground">{value}</p>
      </div>
      <div 
        className="flex h-10 w-10 items-center justify-center rounded-2xl"
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
  const t = useI18nStore((s) => s.t)
  const language = useI18nStore((s) => s.language)
  const [isHovered, setIsHovered] = useState(false)
  const dateLocale = language === "zh-CN" ? "zh-CN" : "en-US"
  
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
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -12 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      className={cn(
        "group cursor-pointer rounded-[24px] border border-border/80 bg-background p-4 transition-all duration-200",
        isHovered ? "shadow-ds-shell" : "shadow-ds-surface"
      )}
      onClick={onView}
    >
      <div className="flex items-start gap-3">
        {/* 文件图标 */}
        <div 
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl"
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
            <span>{t("documents.chunkCount", { count: doc.chunks })}</span>
            <span>{doc.date ? new Date(doc.date).toLocaleDateString(dateLocale, { year: 'numeric', month: '2-digit', day: '2-digit' }) : "—"}</span>
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
            className="rounded-full p-2 text-slate-500 transition-colors hover:bg-secondary"
            title={t("documents.preview")}
          >
            <Eye className="h-4 w-4" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete() }}
            disabled={isDeleting}
            className={cn(
              "rounded-full p-2 transition-colors hover:bg-red-50 dark:hover:bg-red-900/30",
              isDeleting ? "text-slate-400 dark:text-slate-500" : "text-red-500 dark:text-red-400"
            )}
            title={t("documents.delete")}
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
  const t = useI18nStore((s) => s.t)
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
        "cursor-pointer rounded-[24px] border p-3 transition-all duration-200",
        isHovered ? "shadow-ds-shell" : "shadow-ds-surface",
        isSelected 
          ? "border-[#b7c8fe] bg-[#edf3fe] dark:bg-blue-950/40" 
          : "border-border/80 bg-background"
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <div 
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-2xl",
              isSelected ? "bg-white/80 dark:bg-blue-900/50" : "bg-[#edf3fe] dark:bg-blue-950/60"
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
                <span className="rounded-full bg-primary px-2 py-0.5 text-xs text-white">
                  {t("documents.uploadTargetBadge")}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">{t("documents.segmentCount", { count: collection.count })}</p>
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
            className="rounded-full p-1.5 text-slate-500 transition-colors hover:bg-secondary"
            title={t("common.rename")}
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={onDelete}
            disabled={isDeleting}
            className={cn(
              "rounded-full p-1.5 transition-colors hover:bg-red-50 dark:hover:bg-red-900/30",
              isDeleting ? "text-slate-400 dark:text-slate-500" : "text-red-500 dark:text-red-400"
            )}
            title={t("documents.deleteCollection")}
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
  const t = useI18nStore((s) => s.t)
  const config = {
    literature: {
      icon: <FileText className="h-12 w-12" />,
      title: t("documents.emptyNoContent"),
      description: t("documents.emptyNoContentDesc"),
      action: t("documents.upload"),
    },
    collection: {
      icon: <FolderOpen className="h-10 w-10" />,
      title: t("documents.emptyNoCollection"),
      description: t("documents.emptyNoCollectionDesc"),
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
      <div className="mb-4 rounded-full bg-secondary p-4 text-slate-500 dark:text-slate-400">
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

const ConfirmModal: React.FC<ConfirmModalProps> = ({ isOpen, title, message, onConfirm, onCancel, isLoading }) => {
  const t = useI18nStore((s) => s.t)
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
          className="shadow-ds-shell mx-4 w-full max-w-sm rounded-[28px] border border-border/80 bg-white p-6 dark:bg-card"
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
              className="rounded-full bg-secondary px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary/80"
            >
              {t("common.cancel")}
            </button>
            <button
              onClick={onConfirm}
              disabled={isLoading}
              className="flex items-center gap-2 rounded-full bg-red-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-600"
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("documents.confirmDeleteBtn")}
            </button>
          </div>
        </motion.div>
      </motion.div>
    )}
  </AnimatePresence>
  )
}

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
  const t = useI18nStore((s) => s.t)
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
          className="shadow-ds-shell mx-4 w-full max-w-sm rounded-[28px] border border-border/80 bg-white p-6 dark:bg-card"
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
              className="mb-4 w-full rounded-2xl border border-border/80 bg-background px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-0"
              onKeyDown={(e) => e.key === 'Enter' && handleConfirm()}
              autoFocus
            />
            
            <p className="text-xs mb-4 text-slate-500 dark:text-slate-400">
              {t("documents.nameValidation")}
            </p>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={onCancel}
                disabled={isLoading}
                className="rounded-full bg-secondary px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary/80"
              >
                {t("common.cancel")}
              </button>
              <button
                onClick={handleConfirm}
                disabled={isLoading || !value.trim()}
                className="flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/95 disabled:opacity-50"
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
          "shadow-ds-shell fixed right-6 top-6 z-50 flex items-center gap-2 rounded-full px-4 py-3 text-sm font-medium text-white",
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
          className="shadow-ds-shell mx-4 w-full max-w-sm rounded-[28px] border border-border/80 bg-white p-8 text-center dark:bg-card"
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
}) => {
  const t = useI18nStore((s) => s.t)
  return (
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
            alt={t("documents.imageAlt", { index: currentIndex + 1 })}
            className="max-w-full max-h-[85vh] object-contain rounded-lg"
          />
          
          {/* 图片信息 */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/60 text-white px-4 py-2 rounded-lg text-sm">
            {t("documents.pageImageInfo", { page: image.page, current: currentIndex + 1, total: totalCount, width: image.width, height: image.height })}
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
}

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
  const t = useI18nStore((s) => s.t)
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
            className="shadow-ds-shell flex max-h-[85vh] w-full max-w-4xl flex-col overflow-hidden rounded-[32px] border border-border/80 bg-white dark:bg-card"
          >
              {/* 头部 */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#edf3fe] dark:bg-blue-950/60">
                    <FileText className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-lg font-semibold truncate text-slate-800 dark:text-slate-200">{doc?.source || t("documents.fileContentTitle")}</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {t("documents.segmentCount", { count: doc?.chunks ?? 0 })} · {doc?.collection || t("documents.defaultCollection")}
                      {hasImages && ` · ${t("documents.imageCountShort", { count: images.length })}`}
                    </p>
                  </div>
                </div>
                <button onClick={onClose} className="rounded-full p-2 transition-colors hover:bg-secondary">
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
                        ? "bg-[#edf3fe] text-primary" 
                        : "text-slate-600 dark:text-slate-300 hover:bg-secondary"
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      {t("documents.textContent")}
                    </span>
                  </button>
                  <button
                    onClick={() => setActiveTab('images')}
                    className={cn(
                      "px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                      activeTab === 'images' 
                        ? "bg-[#edf3fe] text-primary" 
                        : "text-slate-600 dark:text-slate-300 hover:bg-secondary"
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      {t("documents.imagesTab", { count: images.length })}
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
                    placeholder={t("documents.editContentPlaceholder")}
                  />
                ) : activeTab === 'text' ? (
                  <div className="h-[50vh] overflow-auto rounded-[24px] bg-secondary p-4">
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
                        <p className="text-sm">{t("documents.noImagesInFile")}</p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                        {images.map((img, index) => (
                          <motion.div
                            key={`${img.page}-${img.index}`}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: index * 0.05 }}
                            className="group relative cursor-pointer overflow-hidden rounded-[20px] border border-border/80 shadow-ds-surface"
                            onClick={() => openImageViewer(index)}
                          >
                            <div className="aspect-[4/3] bg-slate-100 dark:bg-slate-700">
                              <img 
                                src={img.base64} 
                                alt={t("chat.sourceImageAlt", { source: doc?.source || "", page: img.page })}
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
                              {t("documents.pageImageInfo", { page: img.page, current: img.index + 1, total: images.length, width: img.width, height: img.height })}
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
                      className="flex items-center gap-2 rounded-full bg-secondary px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary/80"
                    >
                      <X className="h-4 w-4" /> {t("common.cancel")}
                    </button>
                    <button
                      onClick={onSave}
                      disabled={isSaving || !editedContent.trim()}
                      className="flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/95"
                    >
                      {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                      {t("common.save")}
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={onClose}
                      className="rounded-full bg-secondary px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary/80"
                    >
                      {t("common.close")}
                    </button>
                    <button
                      onClick={onEdit}
                      disabled={isLoading}
                      className="flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/95"
                    >
                      <Edit className="h-4 w-4" /> {t("common.edit")}
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
  const t = useI18nStore((s) => s.t)
  const language = useI18nStore((s) => s.language)

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
    const intervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null)
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

  // 文件上传（支持批量）
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setIsUploading(true)
    const targetCollection = selectedCollection || undefined
    const fileList = Array.from(files)

    if (fileList.length === 1) {
      startProgress(t("documents.progressUploadFile"), t("documents.uploadFileProcessing", { name: fileList[0].name }))
      try {
        const result = await chatService.uploadDocument(fileList[0], targetCollection)
        await Promise.all([fetchDocuments(selectedFileType), fetchCollections(), fetchFileTypeStats()])
        await completeProgress()
        showToast(t("documents.uploadSuccessDetail", { message: result.message || '' }), 'success')
      } catch (error: any) {
        cancelProgress()
        showToast(t("documents.uploadFailed", { detail: error.response?.data?.detail || error.message }), 'error')
      } finally {
        setIsUploading(false)
        e.target.value = ""
      }
    } else {
      startProgress(t("documents.progressBatchUpload"), t("documents.uploadBatchProcessing", { count: fileList.length }))
      try {
        const result = await chatService.uploadDocumentsBatch(fileList, targetCollection)
        await Promise.all([fetchDocuments(selectedFileType), fetchCollections(), fetchFileTypeStats()])
        await completeProgress()
        const ok = result.results?.length || 0
        const err = result.errors?.length || 0
        const failedSuffix = err > 0 ? (language === "zh-CN" ? `, ${err} 失败` : `, ${err} failed`) : ""
        showToast(t("documents.uploadBatchResult", { ok, failed: failedSuffix }), err > 0 ? 'error' : 'success')
      } catch (error: any) {
        cancelProgress()
        showToast(t("documents.uploadBatchFailed", { detail: error.response?.data?.detail || error.message }), 'error')
      } finally {
        setIsUploading(false)
        e.target.value = ""
      }
    }
  }

  // 重建索引
  const handleRebuildIndex = async () => {
    setIsRebuilding(true)
    startProgress(t("documents.progressRebuild"), t("documents.scanDirSubtitle"))
    
    try {
      const result = await chatService.rebuildIndex()
      updateMessage(t("documents.progressUpdating"))
      await Promise.all([fetchDocuments(selectedFileType), fetchCollections(), fetchFileTypeStats()])
      await completeProgress()
      
      if (result.num_documents === 0 && result.num_chunks === 0) {
        showToast(t("documents.rebuildNoNewFiles"), 'success')
      } else {
        showToast(t("documents.rebuildSuccess", { files: result.num_documents || 0, chunks: result.num_chunks || 0 }), 'success')
      }
    } catch (error: any) {
      cancelProgress()
      showToast(t("documents.rebuildFailed", { detail: error.response?.data?.detail || error.message }), 'error')
    } finally {
      setIsRebuilding(false)
    }
  }

  // 删除文献
  const handleDeleteDocument = (source: string, collection?: string) => {
    setConfirmModal({
      isOpen: true,
      title: t("documents.deleteFileTitle"),
      message: t("documents.deleteFileMessage", { name: source }),
      onConfirm: async () => {
        setDeletingDoc(source)
        setConfirmModal(prev => ({ ...prev, isOpen: false }))
        startProgress(t("documents.progressDeleteFile"), `${source}...`)
        
        try {
          await chatService.deleteDocumentBySource(source, collection)
          updateMessage(t("documents.progressUpdating"))
          await Promise.all([fetchDocuments(selectedFileType), fetchCollections(), fetchFileTypeStats()])
          await completeProgress()
          showToast(t("documents.deleteFileSuccess"), 'success')
        } catch (error: any) {
          cancelProgress()
          showToast(t("documents.deleteFailed", { detail: error.response?.data?.detail || error.message }), 'error')
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
      title: t("documents.deleteCollectionTitle"),
      message: t("documents.deleteCollectionMessage", { name }),
      onConfirm: async () => {
        setDeletingCollection(name)
        setConfirmModal(prev => ({ ...prev, isOpen: false }))
        startProgress(t("documents.progressDeleteCollection"), `${name}...`)
        
        try {
          await chatService.deleteCollection(name)
          updateMessage(t("documents.progressUpdating"))
          await Promise.all([fetchDocuments(selectedFileType), fetchCollections(), fetchFileTypeStats()])
          await completeProgress()
          showToast(t("documents.deleteCollectionSuccess"), 'success')
        } catch (error: any) {
          cancelProgress()
          showToast(t("documents.deleteFailed", { detail: error.response?.data?.detail || error.message }), 'error')
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
      title: t("documents.createCollectionTitle"),
      placeholder: t("documents.createCollectionPlaceholder"),
      defaultValue: "",
      confirmText: t("documents.createBtn"),
      isLoading: false,
      onConfirm: async (name: string) => {
        setInputModal(prev => ({ ...prev, isLoading: true }))
        startProgress(t("documents.progressCreateCollection"), `${name}...`)
        
        try {
          await chatService.createCollection(name)
          updateMessage(t("documents.progressUpdating"))
          await fetchCollections()
          await completeProgress()
          showToast(t("documents.createCollectionSuccess", { name }), 'success')
          setInputModal(prev => ({ ...prev, isOpen: false }))
        } catch (error: any) {
          cancelProgress()
          showToast(t("documents.createCollectionFailed", { detail: error.response?.data?.detail || error.message }), 'error')
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
      title: t("documents.renameCollectionTitle"),
      placeholder: t("documents.renamePlaceholder"),
      defaultValue: oldName,
      confirmText: t("common.confirm"),
      isLoading: false,
      onConfirm: async (newName: string) => {
        if (newName === oldName) {
          setInputModal(prev => ({ ...prev, isOpen: false }))
          return
        }
        
        setInputModal(prev => ({ ...prev, isLoading: true }))
        startProgress(t("documents.progressRenameCollection"), `${oldName} → ${newName}`)
        
        try {
          await chatService.renameCollection(oldName, newName)
          updateMessage(t("documents.progressUpdating"))
          await Promise.all([fetchDocuments(selectedFileType), fetchCollections(), fetchFileTypeStats()])
          await completeProgress()
          showToast(t("documents.renameCollectionSuccess", { name: newName }), 'success')
          setInputModal(prev => ({ ...prev, isOpen: false }))
        } catch (error: any) {
          cancelProgress()
          showToast(t("documents.renameCollectionFailed", { detail: error.response?.data?.detail || error.message }), 'error')
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
      setDocContent(t("documents.fetchContentFailed", { detail: error.response?.data?.detail || error.message }))
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
      showToast(t("documents.saveContentSuccess"), 'success')
    } catch (error: any) {
      showToast(t("documents.saveContentFailed", { detail: error.response?.data?.detail || error.message }), 'error')
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
    <div className="h-full overflow-auto bg-background">
      <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-5 px-6 py-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <h1 className="text-xl font-semibold text-foreground">{t("documents.title")}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{t("documents.pageDescQuiet")}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {selectedCollection && (
              <span className="rounded-full border border-[#b7c8fe] bg-[#edf3fe] px-3 py-1.5 text-sm text-primary">
                {t("documents.uploadTarget", { name: selectedCollection })}
              </span>
            )}
            <button
              onClick={handleRebuildIndex}
              disabled={isRebuilding}
              className={cn(
                "inline-flex items-center gap-2 rounded-full border border-border/80 px-4 py-2 text-sm transition-colors",
                isRebuilding ? "text-muted-foreground" : "hover:bg-secondary"
              )}
            >
              {isRebuilding ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              {t("documents.scanDirectory")}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleFileUpload}
              accept=".txt,.md,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
              disabled={isUploading}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/95 disabled:opacity-50"
            >
              {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              {t("documents.upload")}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard title={t("documents.statTotalFiles")} value={totalFiles} icon={<FolderOpen className="h-5 w-5" />} color={colors.primary} />
          <StatCard title={t("documents.statTotalChunks")} value={totalChunks} icon={<FileText className="h-5 w-5" />} color="#00B42A" />
          <StatCard title={t("documents.statCollections")} value={collections.length} icon={<Database className="h-5 w-5" />} color="#722ED1" />
          <StatCard title={t("documents.statFileTypes")} value={activeFileTypes.length} icon={<Files className="h-5 w-5" />} color="#FF7D00" />
        </div>

        <div className="rounded-[28px] border border-border/80 bg-white p-3 shadow-ds-surface dark:bg-card">
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-2 text-sm text-muted-foreground">{t("documents.filter")}</span>
          <button
            onClick={() => handleFileTypeChange(null)}
            className={cn(
                "rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
              selectedFileType === null 
                  ? "bg-[#edf3fe] text-primary" 
                  : "text-slate-600 dark:text-slate-300 hover:bg-secondary"
            )}
          >
            {t("documents.allWithCount", { count: totalFiles })}
          </button>
          {activeFileTypes.map((stat) => (
            <button
              key={stat.type}
              onClick={() => handleFileTypeChange(stat.type)}
              className={cn(
                  "rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
                selectedFileType === stat.type 
                    ? "bg-[#edf3fe] text-primary" 
                    : "text-slate-600 dark:text-slate-300 hover:bg-secondary"
              )}
            >
              {stat.label} ({stat.count})
            </button>
          ))}
        </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="rounded-[28px] border border-border/80 bg-white shadow-ds-surface dark:bg-card">
              <div className="flex items-center justify-between border-b border-border/70 px-5 py-4">
                <div>
                  <h2 className="text-base font-medium text-foreground">
                    {selectedFileType ? t("documents.fileTypeFiles", { label: fileTypeStats.find(s => s.type === selectedFileType)?.label || '' }) : t("documents.allFiles")}
                  </h2>
                  <p className="text-xs text-muted-foreground">{t("documents.fileCount", { count: documents.length })}</p>
                </div>
                <div className="rounded-full border border-border/80 px-3 py-1 text-xs text-muted-foreground">
                  {selectedCollection ? t("documents.currentCollection", { name: selectedCollection }) : t("documents.defaultCollection")}
                </div>
              </div>
              
              <div className="max-h-[560px] overflow-auto p-4">
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

          <div className="space-y-4">
            <div className="rounded-[28px] border border-border/80 bg-white shadow-ds-surface dark:bg-card">
              <div className="flex items-center justify-between border-b border-border/70 px-5 py-4">
                <div>
                  <h2 className="flex items-center gap-2 text-base font-medium text-foreground">
                    <Database className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    {t("documents.collections")}
                  </h2>
                  {selectedCollection && (
                    <p className="mt-0.5 text-xs text-blue-600 dark:text-blue-400">
                      {t("documents.collectionSwitchHint")}
                    </p>
                  )}
                </div>
                <button
                  onClick={handleCreateCollection}
                  className="inline-flex items-center gap-1 rounded-full border border-border/80 px-3 py-1.5 text-xs font-medium transition-colors hover:bg-secondary"
                >
                  <Plus className="h-3.5 w-3.5" />
                  {t("documents.newShort")}
                </button>
              </div>
              <div className="max-h-[300px] overflow-auto p-4">
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

            <div className="rounded-[28px] border border-border/80 bg-white p-5 shadow-ds-surface dark:bg-card">
              <h2 className="mb-3 flex items-center gap-2 text-base font-medium text-foreground">
                <RefreshCw className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                {t("documents.batchImport")}
              </h2>
              <button
                onClick={handleRebuildIndex}
                disabled={isRebuilding}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-full border border-border/80 px-4 py-2.5 text-sm font-medium transition-colors",
                  isRebuilding ? "text-slate-400 dark:text-slate-500" : "text-slate-600 dark:text-slate-300 hover:bg-secondary"
                )}
              >
                {isRebuilding ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t("documents.scanning")}
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4" />
                    {t("documents.scanDirectory")}
                  </>
                )}
              </button>
              <p className="mt-3 text-xs text-muted-foreground">
                {t("documents.scanDirSubtitle")}
              </p>
              <div className="mt-4 rounded-[22px] bg-secondary px-4 py-4 text-sm text-muted-foreground">
                {t("documents.batchImportNote")}
              </div>
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
