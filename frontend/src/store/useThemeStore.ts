import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'light' | 'dark' | 'system'

const mediaQuery = typeof window !== 'undefined'
  ? window.matchMedia('(prefers-color-scheme: dark)')
  : null

const getResolvedTheme = (theme: Theme): 'light' | 'dark' => {
  if (theme === 'system') {
    return mediaQuery?.matches ? 'dark' : 'light'
  }
  return theme
}

const applyTheme = (theme: Theme) => {
  if (typeof document === 'undefined') return
  document.documentElement.classList.toggle('dark', getResolvedTheme(theme) === 'dark')
}

interface ThemeStore {
  theme: Theme
  resolvedTheme: 'light' | 'dark'
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set) => ({
      theme: 'system',
      resolvedTheme: getResolvedTheme('system'),
      setTheme: (theme) => {
        applyTheme(theme)
        set({ theme, resolvedTheme: getResolvedTheme(theme) })
      },
      toggleTheme: () =>
        set((state) => {
          const newTheme: Theme = getResolvedTheme(state.theme) === 'dark' ? 'light' : 'dark'
          applyTheme(newTheme)
          return { theme: newTheme, resolvedTheme: getResolvedTheme(newTheme) }
        }),
    }),
    {
      name: 'theme-storage',
    }
  )
)

if (mediaQuery) {
  mediaQuery.addEventListener('change', () => {
    const state = useThemeStore.getState()
    if (state.theme === 'system') {
      const resolvedTheme = getResolvedTheme('system')
      applyTheme('system')
      useThemeStore.setState({ resolvedTheme })
    }
  })
}

applyTheme(useThemeStore.getState().theme)
