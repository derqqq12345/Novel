import { useState } from 'react'
import type {
  Character,
  PlotPoint,
  WorldBuilding,
  ConsistencyIssue,
} from '../../types'

interface ContextSidebarProps {
  characters: Character[]
  plotPoints: PlotPoint[]
  worldBuilding: WorldBuilding[]
  consistencyScore: number | null
  consistencyIssues: ConsistencyIssue[]
  onCharacterClick?: (characterId: string) => void
  onPlotPointClick?: (plotPointId: string) => void
  onWorldBuildingClick?: (worldBuildingId: string) => void
}

type TabType = 'characters' | 'plot' | 'worldbuilding' | 'consistency'

export default function ContextSidebar({
  characters,
  plotPoints,
  worldBuilding,
  consistencyScore,
  consistencyIssues,
  onCharacterClick,
  onPlotPointClick,
  onWorldBuildingClick,
}: ContextSidebarProps) {
  const [activeTab, setActiveTab] = useState<TabType>('characters')

  const plotStageLabels: Record<string, string> = {
    exposition: '발단',
    rising_action: '전개',
    climax: '절정',
    falling_action: '하강',
    resolution: '결말',
  }

  const worldbuildingCategoryLabels: Record<string, string> = {
    location: '장소',
    magic_system: '마법 체계',
    technology: '기술',
    culture: '문화',
  }

  const tabs: { id: TabType; label: string; count?: number }[] = [
    { id: 'characters', label: '캐릭터', count: characters.length },
    { id: 'plot', label: '플롯', count: plotPoints.length },
    { id: 'worldbuilding', label: '세계관', count: worldBuilding.length },
    {
      id: 'consistency',
      label: '일관성',
      count: consistencyIssues.filter((i) => !i.is_resolved).length,
    },
  ]

  return (
    <div className="h-full bg-white dark:bg-slate-800 border-l border-slate-200 dark:border-slate-700 flex flex-col">
      {/* 탭 헤더 */}
      <div className="flex border-b border-slate-200 dark:border-slate-700 shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 py-2.5 text-xs font-medium transition relative ${
              activeTab === tab.id
                ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-600'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            {tab.label}
            {tab.count !== undefined && tab.count > 0 && (
              <span
                className={`ml-1 px-1.5 py-0.5 text-xs rounded-full ${
                  activeTab === tab.id
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* 탭 컨텐츠 */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* 캐릭터 탭 */}
        {activeTab === 'characters' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                등장인물
              </span>
            </div>
            {characters.length === 0 ? (
              <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-4">
                등록된 캐릭터가 없습니다
              </p>
            ) : (
              characters.map((char) => (
                <div
                  key={char.id}
                  onClick={() => onCharacterClick?.(char.id)}
                  className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-slate-800 dark:text-slate-200">
                      {char.name}
                    </span>
                    {char.age && (
                      <span className="text-xs text-slate-400">
                        {char.age}세
                      </span>
                    )}
                  </div>
                  {char.personality_traits.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {char.personality_traits.slice(0, 3).map((trait) => (
                        <span
                          key={trait}
                          className="text-xs px-2 py-0.5 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full"
                        >
                          {trait}
                        </span>
                      ))}
                      {char.personality_traits.length > 3 && (
                        <span className="text-xs text-slate-400">
                          +{char.personality_traits.length - 3}
                        </span>
                      )}
                    </div>
                  )}
                  {char.appearance && (
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 line-clamp-2">
                      {char.appearance}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* 플롯 탭 */}
        {activeTab === 'plot' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                플롯 구조
              </span>
            </div>
            {plotPoints.length === 0 ? (
              <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-4">
                등록된 플롯이 없습니다
              </p>
            ) : (
              <>
                {/* 플롯 타임라인 시각화 */}
                <div className="mb-4">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                    <span>발단</span>
                    <span>전개</span>
                    <span>절정</span>
                    <span>하강</span>
                    <span>결말</span>
                  </div>
                  <div className="relative h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    {['exposition', 'rising_action', 'climax', 'falling_action', 'resolution'].map(
                      (stage, index) => {
                        const stagePoints = plotPoints.filter(
                          (p) => p.plot_stage === stage
                        )
                        const completedCount = stagePoints.filter(
                          (p) => p.is_completed
                        ).length
                        const progress =
                          stagePoints.length > 0
                            ? (completedCount / stagePoints.length) * 100
                            : 0
                        return (
                          <div
                            key={stage}
                            className="absolute h-full"
                            style={{
                              left: `${index * 20}%`,
                              width: '20%',
                            }}
                          >
                            <div
                              className="h-full bg-primary-500 transition-all"
                              style={{ width: `${progress}%` }}
                            />
                          </div>
                        )
                      }
                    )}
                  </div>
                </div>

                {/* 플롯 포인트 목록 */}
                {plotPoints.map((point) => (
                  <div
                    key={point.id}
                    onClick={() => onPlotPointClick?.(point.id)}
                    className={`p-3 rounded-lg border cursor-pointer transition ${
                      point.is_completed
                        ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                        : 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <span
                        className={`mt-0.5 text-sm ${
                          point.is_completed
                            ? 'text-green-500'
                            : 'text-slate-300'
                        }`}
                      >
                        {point.is_completed ? '✓' : '○'}
                      </span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                          {point.title}
                        </p>
                        <p className="text-xs text-slate-400 mt-0.5">
                          {plotStageLabels[point.plot_stage]}
                          {point.target_chapter && ` • 챕터 ${point.target_chapter}`}
                        </p>
                        {point.description && (
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                            {point.description}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {/* 세계관 탭 */}
        {activeTab === 'worldbuilding' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                세계관 설정
              </span>
            </div>
            {worldBuilding.length === 0 ? (
              <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-4">
                등록된 세계관이 없습니다
              </p>
            ) : (
              worldBuilding.map((item) => (
                <div
                  key={item.id}
                  onClick={() => onWorldBuildingClick?.(item.id)}
                  className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-slate-800 dark:text-slate-200">
                      {item.name}
                    </span>
                    <span className="text-xs px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-full">
                      {worldbuildingCategoryLabels[item.category]}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                    {item.description}
                  </p>
                </div>
              ))
            )}
          </div>
        )}

        {/* 일관성 탭 */}
        {activeTab === 'consistency' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                일관성 분석
              </span>
            </div>

            {/* 일관성 점수 */}
            {consistencyScore !== null && (
              <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
                    전체 점수
                  </span>
                  <span
                    className={`text-lg font-bold ${
                      consistencyScore >= 90
                        ? 'text-green-600 dark:text-green-400'
                        : consistencyScore >= 70
                        ? 'text-yellow-600 dark:text-yellow-400'
                        : 'text-red-600 dark:text-red-400'
                    }`}
                  >
                    {consistencyScore}
                  </span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      consistencyScore >= 90
                        ? 'bg-green-500'
                        : consistencyScore >= 70
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${consistencyScore}%` }}
                  />
                </div>
              </div>
            )}

            {/* 일관성 이슈 목록 */}
            {consistencyIssues.length === 0 ? (
              <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-4">
                {consistencyScore !== null
                  ? '발견된 이슈가 없습니다 ✓'
                  : '일관성 검사를 실행하세요'}
              </p>
            ) : (
              <div className="space-y-2">
                {consistencyIssues
                  .filter((issue) => !issue.is_resolved)
                  .map((issue) => (
                    <div
                      key={issue.id}
                      className={`p-3 rounded-lg border ${
                        issue.severity === 'high'
                          ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                          : issue.severity === 'medium'
                          ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
                          : 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-white dark:bg-slate-800">
                          {issue.issue_type === 'character'
                            ? '캐릭터'
                            : issue.issue_type === 'plot'
                            ? '플롯'
                            : '세계관'}
                        </span>
                        <div className="flex-1">
                          <p className="text-xs text-slate-700 dark:text-slate-300">
                            {issue.description}
                          </p>
                          {issue.line_number && (
                            <p className="text-xs text-slate-400 mt-1">
                              라인 {issue.line_number}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 하단 일관성 점수 (고정) */}
      {consistencyScore !== null && (
        <div className="p-4 border-t border-slate-200 dark:border-slate-700 shrink-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
              현재 챕터 일관성
            </span>
            <span
              className={`text-sm font-bold ${
                consistencyScore >= 90
                  ? 'text-green-600 dark:text-green-400'
                  : consistencyScore >= 70
                  ? 'text-yellow-600 dark:text-yellow-400'
                  : 'text-red-600 dark:text-red-400'
              }`}
            >
              {consistencyScore}
            </span>
          </div>
          <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5">
            <div
              className={`h-1.5 rounded-full transition-all ${
                consistencyScore >= 90
                  ? 'bg-green-500'
                  : consistencyScore >= 70
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${consistencyScore}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
