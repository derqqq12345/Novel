import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'
import Input from '@/components/ui/Input'
import Button from '@/components/ui/Button'

// Zod 스키마 정의
const registerSchema = z.object({
  username: z
    .string()
    .min(1, '이름을 입력해주세요')
    .min(2, '이름은 최소 2자 이상이어야 합니다')
    .max(50, '이름은 최대 50자까지 입력 가능합니다'),
  email: z
    .string()
    .min(1, '이메일을 입력해주세요')
    .email('올바른 이메일 형식이 아닙니다'),
  password: z
    .string()
    .min(1, '비밀번호를 입력해주세요')
    .min(6, '비밀번호는 최소 6자 이상이어야 합니다')
    .max(100, '비밀번호는 최대 100자까지 입력 가능합니다'),
})

type RegisterFormData = z.infer<typeof registerSchema>

// 비밀번호 강도 계산 함수
const calculatePasswordStrength = (password: string): {
  strength: number
  label: string
  color: string
} => {
  if (!password) {
    return { strength: 0, label: '', color: '' }
  }

  let strength = 0

  // 길이 체크
  if (password.length >= 6) strength += 1
  if (password.length >= 10) strength += 1

  // 대문자 포함
  if (/[A-Z]/.test(password)) strength += 1

  // 소문자 포함
  if (/[a-z]/.test(password)) strength += 1

  // 숫자 포함
  if (/[0-9]/.test(password)) strength += 1

  // 특수문자 포함
  if (/[^A-Za-z0-9]/.test(password)) strength += 1

  // 강도 레벨 결정
  if (strength <= 2) {
    return { strength: 1, label: '약함', color: 'bg-red-500' }
  } else if (strength <= 4) {
    return { strength: 2, label: '보통', color: 'bg-yellow-500' }
  } else {
    return { strength: 3, label: '강함', color: 'bg-green-500' }
  }
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const setUser = useAuthStore((state) => state.setUser)
  const [apiError, setApiError] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  })

  const password = watch('password', '')
  const passwordStrength = calculatePasswordStrength(password)

  const onSubmit = async (data: RegisterFormData) => {
    try {
      setIsLoading(true)
      setApiError('')

      // API 호출
      await authApi.register(data)

      // 회원가입 후 자동 로그인
      const tokens = await authApi.login({
        email: data.email,
        password: data.password,
      })

      // 토큰 저장
      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)

      // 사용자 정보 가져오기
      const user = await authApi.me()
      setUser(user)

      // 대시보드로 이동
      navigate('/dashboard')
    } catch (error: any) {
      console.error('Register error:', error)

      // 에러 메시지 처리
      if (error.response?.data?.detail) {
        setApiError(error.response.data.detail)
      } else if (error.response?.status === 400) {
        setApiError('이미 사용 중인 이메일입니다')
      } else if (error.response?.status === 422) {
        setApiError('입력 정보를 확인해주세요')
      } else {
        setApiError('회원가입 중 오류가 발생했습니다. 다시 시도해주세요.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-indigo-100 dark:from-slate-900 dark:to-slate-800 px-4">
      <div className="w-full max-w-md">
        {/* 로고 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-primary-600 rounded-2xl mb-4 shadow-lg">
            <span className="text-white text-2xl">✍️</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">AI 소설 플랫폼</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">새 계정을 만드세요</p>
        </div>

        {/* 카드 */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-8">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* API 에러 메시지 */}
            {apiError && (
              <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <p className="text-sm text-red-600 dark:text-red-400">{apiError}</p>
              </div>
            )}

            {/* 이름 */}
            <Input
              label="이름"
              type="text"
              placeholder="홍길동"
              error={errors.username?.message}
              {...register('username')}
            />

            {/* 이메일 */}
            <Input
              label="이메일"
              type="email"
              placeholder="you@example.com"
              error={errors.email?.message}
              {...register('email')}
            />

            {/* 비밀번호 */}
            <div>
              <Input
                label="비밀번호"
                type="password"
                placeholder="••••••••"
                error={errors.password?.message}
                {...register('password')}
              />

              {/* 비밀번호 강도 표시 */}
              {password && (
                <div className="mt-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-slate-600 dark:text-slate-400">
                      비밀번호 강도:
                    </span>
                    <span
                      className={`text-xs font-medium ${
                        passwordStrength.strength === 1
                          ? 'text-red-600 dark:text-red-400'
                          : passwordStrength.strength === 2
                          ? 'text-yellow-600 dark:text-yellow-400'
                          : 'text-green-600 dark:text-green-400'
                      }`}
                    >
                      {passwordStrength.label}
                    </span>
                  </div>
                  <div className="flex gap-1">
                    {[1, 2, 3].map((level) => (
                      <div
                        key={level}
                        className={`h-1.5 flex-1 rounded-full transition-colors ${
                          level <= passwordStrength.strength
                            ? passwordStrength.color
                            : 'bg-slate-200 dark:bg-slate-700'
                        }`}
                      />
                    ))}
                  </div>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    대문자, 소문자, 숫자, 특수문자를 포함하면 더 안전합니다
                  </p>
                </div>
              )}
            </div>

            {/* 회원가입 버튼 */}
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isLoading}
              className="w-full"
            >
              회원가입
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
            이미 계정이 있으신가요?{' '}
            <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
              로그인
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
