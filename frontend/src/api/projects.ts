import { apiClient } from './client'
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  PaginatedResponse,
} from '@/types'

export const projectsApi = {
  list: async (page = 1, size = 20): Promise<PaginatedResponse<Project>> => {
    const res = await apiClient.get<PaginatedResponse<Project>>('/projects', {
      params: { page, size },
    })
    return res.data
  },

  get: async (id: string): Promise<Project> => {
    const res = await apiClient.get<Project>(`/projects/${id}`)
    return res.data
  },

  create: async (data: ProjectCreate): Promise<Project> => {
    const res = await apiClient.post<Project>('/projects', data)
    return res.data
  },

  update: async (id: string, data: ProjectUpdate): Promise<Project> => {
    const res = await apiClient.put<Project>(`/projects/${id}`, data)
    return res.data
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/projects/${id}`)
  },

  export: async (
    id: string,
    format: 'pdf' | 'epub' | 'txt',
    options?: Record<string, unknown>,
  ): Promise<{ download_url: string; task_id: string }> => {
    const res = await apiClient.post(`/projects/${id}/export`, {
      format,
      ...options,
    })
    return res.data
  },
}
