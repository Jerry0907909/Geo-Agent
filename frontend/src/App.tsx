import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/useAuthStore'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import ChatPage from './pages/ChatPage'
import DocumentsPage from './pages/DocumentsPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'

const ProtectedRoute = ({ children }: { children: JSX.Element }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  return children
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        {/* 根路径重定向到首页 */}
        <Route path="/" element={<Navigate to="/home" replace />} />
        
        {/* HomePage 独立显示，全屏无侧边栏 */}
        <Route path="/home" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
        
        {/* 带侧边栏的功能页面 */}
        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route path="chat" element={<ChatPage />} />
          <Route path="chat/:conversationId" element={<ChatPage />} />
          <Route path="documents" element={<DocumentsPage />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
