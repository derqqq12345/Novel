import { apiClient } from './client'
import type { Character, CharacterCreate, CharacterUpdate } from '../types'

export const charactersApi = {
  // 캐릭터 목록 조회
  list: async (projectId: string): Promise<Character[]> => {
    const res = await apiClient.get<Character[]>(
      `/projects/${projectId}/characters`
    )
    return res.data
  },

  // 캐릭터 생성
  create: async (
    projectId: string,
    data: CharacterCreate
  ): Promise<Character> => {
    const res = await apiClient.post<Character>(
      `/projects/${projectId}/characters`,
      data
    )
    return res.data
  },

  // 캐릭터 수정
  update: async (
    characterId: string,
    data: CharacterUpdate
  ): Promise<Character> => {
    const res = await apiClient.put<Character>(
      `/characters/${characterId}`,
      data
    )
    return res.data
  },

  // 캐릭터 삭제
  delete: async (characterId: string): Promise<void> => {
    await apiClient.delete(`/characters/${characterId}`)
  },
}
