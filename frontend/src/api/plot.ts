import { apiClient } from './client'
import type { PlotPoint, PlotPointCreate } from '../types'

export const plotApi = {
  // 플롯 포인트 목록 조회
  list: async (projectId: string): Promise<PlotPoint[]> => {
    const res = await apiClient.get<PlotPoint[]>(`/projects/${projectId}/plot`)
    return res.data
  },

  // 플롯 포인트 업데이트 (전체 교체)
  update: async (
    projectId: string,
    plotPoints: PlotPointCreate[]
  ): Promise<PlotPoint[]> => {
    const res = await apiClient.put<PlotPoint[]>(
      `/projects/${projectId}/plot`,
      { plot_points: plotPoints }
    )
    return res.data
  },

  // 플롯 포인트 완료 표시
  markComplete: async (
    plotPointId: string,
    isCompleted: boolean
  ): Promise<PlotPoint> => {
    const res = await apiClient.patch<PlotPoint>(`/plot/${plotPointId}`, {
      is_completed: isCompleted,
    })
    return res.data
  },
}
