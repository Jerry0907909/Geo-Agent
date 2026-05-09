import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import { useThemeStore } from './store/useThemeStore'

const savedTheme = useThemeStore.getState().theme
document.documentElement.classList.toggle('dark', savedTheme === 'dark')

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
