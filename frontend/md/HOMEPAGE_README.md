# 地质文献智能体 - 主页动画实现文档

## 概述
本项目实现了一个具有极强视觉冲击力的主页，采用 **拟物化（Skeuomorphism）** 和 **玻璃拟态（Glassmorphism）** 设计风格，配合 Framer Motion 实现流畅的动画效果。

## 技术栈
- **React 18** - 函数式组件
- **Framer Motion** - 动画库
- **Tailwind CSS** - 样式框架
- **React Router DOM v6** - 路由管理
- **TypeScript** - 类型安全

## 核心功能

### 1. 主页 (HomePage.tsx)
**位置**: `src/pages/HomePage.tsx`

#### 视觉特性
- **深色渐变背景**: 从 slate-900 到 slate-800 的渐变，营造专业氛围
- **动态背景光效**: 使用脉冲动画的渐变圆形，增加动感
- **三个功能卡片**: 智能问答、文献检索、文献管理

#### 卡片设计特点
1. **3D 透视效果**
   - 使用 `perspective: 1000px` 创建 3D 空间
   - `transform-style: preserve-3d` 保持 3D 变换
   - 悬停时轻微倾斜 (`rotateY: 5, rotateX: -5`)

2. **玻璃拟态效果**
   - 半透明背景 (`bg-white/10`)
   - 背景模糊 (`backdrop-blur-xl`)
   - 白色边框 (`border-white/20`)

3. **多重阴影层次**
   - 外部阴影：营造悬浮感
   - 内部阴影：增加深度
   - 发光效果：悬停时动态颜色发光

4. **动画效果**
   - **进入动画**: 从下方淡入 + 缩放 (stagger 延迟)
   - **悬停动画**: 
     - 卡片放大 1.05 倍
     - 3D 倾斜效果
     - 图标旋转 + 缩放
     - 渐变背景旋转动画
   - **粒子效果**: 悬停时产生上升的彩色粒子

5. **图标容器**
   - 渐变背景色
   - 多重阴影（外发光 + 内高光）
   - 顶部高光条

### 2. 页面过渡 (PageTransition.tsx)
**位置**: `src/components/PageTransition.tsx`

#### 功能
- 包装功能页面，提供统一的进入/退出动画
- 使用 `layoutId` 实现共享元素过渡
- 提供"返回主页"按钮

#### 动画流程
1. **进入**: 
   - 透明度 0 → 1
   - 缩放 0.95 → 1
   - 持续时间 0.4s，使用自定义缓动函数

2. **退出**:
   - 透明度 1 → 0
   - 缩放 1 → 0.9
   - 持续时间 0.3s
   - 平滑回落到原卡片位置

### 3. 页面包装器
**位置**: 
- `src/pages/ChatPageWrapper.tsx`
- `src/pages/SearchPageWrapper.tsx`
- `src/pages/DocumentsPageWrapper.tsx`

每个包装器将对应的功能页面包裹在 `PageTransition` 中，并传递相应的 `layoutId`。

### 4. 路由配置 (App.tsx)
**更新内容**:
- 添加 `AnimatePresence` 支持页面切换动画
- 主页设为根路径 (`/`)
- 功能页面移至子路径 (`/chat`, `/search`, `/documents`)

### 5. 布局更新 (Layout.tsx)
**更新内容**:
- 在主页隐藏侧边栏 (`isHomePage` 判断)
- 更新导航链接指向新路径
- 保持其他页面的侧边栏功能

## 动画参数说明

### 卡片进入动画
```typescript
initial={{ opacity: 0, y: 50, scale: 0.9 }}
animate={{ opacity: 1, y: 0, scale: 1 }}
transition={{
  duration: 0.6,
  delay: index * 0.15,  // 依次延迟
  ease: [0.25, 0.46, 0.45, 0.94]  // 自定义缓动
}
```

### 悬停效果
```typescript
whileHover={{
  scale: 1.05,
  rotateY: 5,
  rotateX: -5,
  z: 50
}}
```

### 页面过渡
```typescript
exit={{ 
  opacity: 0, 
  scale: 0.9,
  transition: { 
    duration: 0.3,
    ease: [0.43, 0.13, 0.23, 0.96]
  }
}}
```

## 颜色方案

### 卡片主题色
- **智能问答**: 蓝色系 (`blue-500` → `indigo-700`, #3b82f6)
- **文献检索**: 绿色系 (`emerald-500` → `teal-700`, #10b981)
- **文献管理**: 紫色系 (`violet-500` → `fuchsia-700`, #8b5cf6)

### 背景
- 主背景: `slate-900` → `slate-800` 渐变
- 光效: 蓝色和紫色半透明脉冲

## 自定义 CSS 工具类
**位置**: `src/index.css`

```css
.perspective-1000 {
  perspective: 1000px;
}

.preserve-3d {
  transform-style: preserve-3d;
}

.backface-hidden {
  backface-visibility: hidden;
}
```

## 使用方式

### 启动开发服务器
```bash
cd frontend
npm install
npm run dev
```

### 访问路径
- 主页: `http://localhost:5173/`
- 智能问答: `http://localhost:5173/chat`
- 文献检索: `http://localhost:5173/search`
- 文献管理: `http://localhost:5173/documents`

## 性能优化建议

1. **动画性能**
   - 使用 `transform` 和 `opacity` 属性（GPU 加速）
   - 避免动画 `width`、`height` 等触发重排的属性

2. **条件渲染**
   - 粒子效果仅在悬停时渲染
   - 使用 `AnimatePresence` 的 `mode="wait"` 避免重叠

3. **代码分割**
   - 功能页面使用独立组件
   - 按需加载，减少初始包大小

## 扩展建议

1. **添加更多卡片**: 在 `features` 数组中添加新对象
2. **自定义动画**: 修改 `transition` 参数
3. **主题切换**: 添加明暗主题切换功能
4. **响应式优化**: 针对移动端调整卡片布局

## 故障排查

### Framer Motion 类型错误
如果遇到 TypeScript 类型错误，重启 TypeScript 服务器：
- VS Code: `Ctrl+Shift+P` → "TypeScript: Restart TS Server"

### 动画不流畅
- 检查浏览器硬件加速是否开启
- 减少同时运行的动画数量
- 降低粒子效果的数量

## 参考资源
- [Framer Motion 文档](https://www.framer.com/motion/)
- [Tailwind CSS 文档](https://tailwindcss.com/)
- [React Router 文档](https://reactrouter.com/)
