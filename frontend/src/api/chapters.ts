import { apiClient } from './client'
import type {
  Chapter,
  ChapterUpdate,
  ChapterVersion,
  GenerationParameters,
  ConsistencyReport,
} from '../types'

export const chaptersApi = {
  // 챕터 생성 (직접 생성 - AI 생성 후 저장용)
  create: async (
    projectId: string,
    data: {
      title?: string
      content: string
      chapter_number?: number
      word_count?: number
    }
  ): Promise<Chapter> => {
    const res = await apiClient.post<Chapter>(
      `/projects/${projectId}/chapters/generate`,
      data
    )
    return res.data
  },

  // 챕터 생성
  generate: async (
    projectId: string,
    parameters: GenerationParameters
  ): Promise<Chapter> => {
    const res = await apiClient.post<Chapter>(
      `/projects/${projectId}/chapters/generate`,
      parameters
    )
    return res.data
  },

  // 챕터 목록 조회
  list: async (projectId: string): Promise<Chapter[]> => {
    const res = await apiClient.get<{ items: Chapter[]; total: number }>(
      `/projects/${projectId}/chapters`
    )
    return res.data.items // items 배열 반환
  },

  // 챕터 상세 조회
  get: async (chapterId: string): Promise<Chapter> => {
    const res = await apiClient.get<Chapter>(`/chapters/${chapterId}`)
    return res.data
  },

  // 챕터 수정
  update: async (chapterId: string, data: ChapterUpdate): Promise<Chapter> => {
    const res = await apiClient.put<Chapter>(`/chapters/${chapterId}`, data)
    return res.data
  },

  // 챕터 삭제
  delete: async (chapterId: string): Promise<void> => {
    await apiClient.delete(`/chapters/${chapterId}`)
  },

  // 챕터 재생성
  regenerate: async (
    chapterId: string,
    feedback?: string
  ): Promise<Chapter> => {
    const res = await apiClient.post<Chapter>(`/chapters/${chapterId}/regenerate`, {
      feedback,
    })
    return res.data
  },

  // 챕터 버전 히스토리
  getVersions: async (chapterId: string): Promise<ChapterVersion[]> => {
    const res = await apiClient.get<ChapterVersion[]>(
      `/chapters/${chapterId}/versions`
    )
    return res.data
  },

  // 챕터 순서 변경
  reorder: async (projectId: string, chapterIds: string[]): Promise<void> => {
    await apiClient.post(`/projects/${projectId}/chapters/reorder`, {
      chapter_order: chapterIds,
    })
  },

  // 챕터 일관성 검증
  checkConsistency: async (chapterId: string): Promise<ConsistencyReport> => {
    const res = await apiClient.get<ConsistencyReport>(
      `/chapters/${chapterId}/consistency`
    )
    return res.data
  },
}
