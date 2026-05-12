import { create } from 'zustand'
import { User } from '../types'

interface AuthState {
  user: User | null
  setUser: (user: User | null) => void
  logout: () => void
  isAuthenticated: () => boolean
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  
  setUser: (user) => set({ user }),
  
  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null })
  },
  
  isAuthenticated: () => {
    const token = localStorage.getItem('access_token')
    return !!token && !!get().user
  },
}))
