import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { authApi } from '../api'
import { useAuthStore } from '../store/authStore'
import type { LoginRequest, RegisterRequest } from '../api/auth'

export function useAuth() {
  const queryClient = useQueryClient()
  const { setUser, logout: logoutStore } = useAuthStore()

  // 현재 사용자 정보 조회
  const { data: user, isLoading } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: authApi.me,
    enabled: !!localStorage.getItem('access_token'),
    retry: false,
    staleTime: 1000 * 60 * 5, // 5분
  })

  // 사용자 정보 동기화
  if (user && user !== useAuthStore.getState().user) {
    setUser(user)
  }

  // 로그인
  const loginMutation = useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: (tokens) => {
      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
      queryClient.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
  })

  // 회원가입
  const registerMutation = useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
  })

  // 로그아웃
  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      logoutStore()
      queryClient.clear()
    },
  })

  return {
    user,
    isLoading,
    login: loginMutation.mutateAsync,
    register: registerMutation.mutateAsync,
    logout: logoutMutation.mutateAsync,
    isLoginLoading: loginMutation.isPending,
    isRegisterLoading: registerMutation.isPending,
  }
}
