import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { projectsApi } from '../api'
import type { ProjectCreate, ProjectUpdate } from '../types'

export function useProjects(page = 1, size = 20) {
  const queryClient = useQueryClient()

  // 프로젝트 목록 조회
  const { data, isLoading, error } = useQuery({
    queryKey: ['projects', page, size],
    queryFn: () => projectsApi.list(page, size),
  })

  // 프로젝트 생성
  const createMutation = useMutation({
    mutationFn: (data: ProjectCreate) => projectsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  // 프로젝트 수정
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProjectUpdate }) =>
      projectsApi.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      queryClient.invalidateQueries({ queryKey: ['project', variables.id] })
    },
  })

  // 프로젝트 삭제
  const deleteMutation = useMutation({
    mutationFn: (id: string) => projectsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  return {
    projects: data?.items ?? [],
    total: data?.total ?? 0,
    pages: data?.pages ?? 0,
    isLoading,
    error,
    createProject: createMutation.mutateAsync,
    updateProject: updateMutation.mutateAsync,
    deleteProject: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  }
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id),
    enabled: !!id,
  })
}
