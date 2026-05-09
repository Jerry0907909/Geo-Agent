import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface RouteStore {
  lastRoute: string
  setLastRoute: (route: string) => void
}

export const useRouteStore = create<RouteStore>()(
  persist(
    (set) => ({
      lastRoute: '/',
      setLastRoute: (route) => set({ lastRoute: route }),
    }),
    {
      name: 'route-storage',
    }
  )
)
