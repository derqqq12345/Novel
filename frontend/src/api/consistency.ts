import { apiClient } from './client'
import type { ConsistencyReport } from '../types'

export const consistencyApi = {
  // 챕터 일관성 검증
  checkChapter: async (chapterId: string): Promise<ConsistencyReport> => {
    const res = await apiClient.get<ConsistencyReport>(
      `/chapters/${chapterId}/consistency`
    )
    return res.data
  },

  // 프로젝트 전체 일관성 검증
  checkProject: async (projectId: string): Promise<ConsistencyReport[]> => {
    const res = await apiClient.get<ConsistencyReport[]>(
      `/projects/${projectId}/consistency`
    )
    return res.data
  },
}
