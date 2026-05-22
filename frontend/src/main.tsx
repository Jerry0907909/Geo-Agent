import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import { useI18nStore } from './i18n'
import { useThemeStore } from './store/useThemeStore'

// Init theme
const savedTheme = useThemeStore.getState().theme
document.documentElement.classList.toggle('dark', savedTheme === 'dark')

// Init i18n BEFORE render (BUG-1: await to avoid race)
const root = document.getElementById('root')!
useI18nStore.getState().init().then(() => {
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
}).catch(() => {
  // Fallback: render even if i18n init fails
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
})
