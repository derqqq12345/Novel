import { apiClient } from './client'
import type { WorldBuilding, WorldBuildingCreate } from '../types'

export const worldbuildingApi = {
  // 세계관 요소 목록 조회
  list: async (projectId: string): Promise<WorldBuilding[]> => {
    const res = await apiClient.get<WorldBuilding[]>(
      `/projects/${projectId}/worldbuilding`
    )
    return res.data
  },

  // 세계관 요소 생성
  create: async (
    projectId: string,
    data: WorldBuildingCreate
  ): Promise<WorldBuilding> => {
    const res = await apiClient.post<WorldBuilding>(
      `/projects/${projectId}/worldbuilding`,
      data
    )
    return res.data
  },

  // 세계관 요소 수정
  update: async (
    worldbuildingId: string,
    data: Partial<WorldBuildingCreate>
  ): Promise<WorldBuilding> => {
    const res = await apiClient.put<WorldBuilding>(
      `/worldbuilding/${worldbuildingId}`,
      data
    )
    return res.data
  },

  // 세계관 요소 삭제
  delete: async (worldbuildingId: string): Promise<void> => {
    await apiClient.delete(`/worldbuilding/${worldbuildingId}`)
  },
}
