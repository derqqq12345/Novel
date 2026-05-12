import { useState, useEffect } from 'react'
import type { Genre, Tone } from '../../types'

interface ChapterGenerationPanelProps {
  projectId: string
  onGenerate: (params: GenerationParams) => void
  onRegenerate: (feedback: string) => void
  isGenerating: boolean
  progress: number
  error: string | null
}

export interface GenerationParams {
  genre: Genre
  tone: Tone
  temperature: number
  userPrompt?: string
}

export default function ChapterGenerationPanel({
  onGenerate,
  onRegenerate,
  isGenerating,
  progress,
  error,
}: ChapterGenerationPanelProps) {
  const [genre, setGenre] = useState<Genre>('fantasy')
  const [tone, setTone] = useState<Tone>('serious')
  const [temperature, setTemperature] = useState(0.7)
  const [userPrompt, setUserPrompt] = useState('')
  const [feedback, setFeedback] = useState('')

  // 생성 이벤트 리스너
  useEffect(() => {
    const handleGenerate = () => {
      if (!isGenerating) {
        onGenerate({ genre, tone, temperature, userPrompt })
      }
    }

    window.addEventListener('editor:generate', handleGenerate)
    return () => window.removeEventListener('editor:generate', handleGenerate)
  }, [genre, tone, temperature, userPrompt, isGenerating, onGenerate])

  const handleGenerate = () => {
    onGenerate({ genre, tone, temperature, userPrompt })
  }

  const handleRegenerate = () => {
    onRegenerate(feedback)
    setFeedback('')
  }

  const genreLabels: Record<Genre, string> = {
    fantasy: '판타지',
    romance: '로맨스',
    mystery: '미스터리',
    science_fiction: 'SF',
    thriller: '스릴러',
  }

  const toneLabels: Record<Tone, string> = {
    serious: '진지함',
    humorous: '유머러스',
    dark: '어두움',
    lighthearted: '가벼움',
  }

  return (
    <div className="space-y-4">
      <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-3">
        생성 파라미터
      </div>

      {/* 장르 선택 */}
      <div>
        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
          장르
        </label>
        <select
          value={genre}
          onChange={(e) => setGenre(e.target.value as Genre)}
          disabled={isGenerating}
          className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
        >
          {Object.entries(genreLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* 톤 선택 */}
      <div>
        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
          톤
        </label>
        <select
          value={tone}
          onChange={(e) => setTone(e.target.value as Tone)}
          disabled={isGenerating}
          className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
        >
          {Object.entries(toneLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* 창의성 슬라이더 */}
      <div>
        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
          창의성{' '}
          <span className="text-primary-500 font-semibold">
            {temperature.toFixed(1)}
          </span>
        </label>
        <input
          type="range"
          min="0.3"
          max="1.2"
          step="0.1"
          value={temperature}
          onChange={(e) => setTemperature(Number(e.target.value))}
          disabled={isGenerating}
          className="w-full accent-primary-600 disabled:opacity-50"
        />
        <div className="flex justify-between text-xs text-slate-400 mt-1">
          <span>일관적 (0.3)</span>
          <span>창의적 (1.2)</span>
        </div>
      </div>

      {/* 사용자 지정 프롬프트 */}
      <div>
        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
          추가 지시사항
        </label>
        <textarea
          value={userPrompt}
          onChange={(e) => setUserPrompt(e.target.value)}
          disabled={isGenerating}
          placeholder="예: 주인공이 적과 처음 대면하는 장면을 써줘..."
          rows={3}
          className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none disabled:opacity-50"
        />
      </div>

      {/* 생성 진행 상태 */}
      {isGenerating && (
        <div>
          <div className="flex justify-between text-xs text-slate-500 mb-1">
            <span>생성 중...</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
            <div
              className="bg-primary-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* 에러 메시지 */}
      {error && (
        <div className="px-3 py-2 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-600 dark:text-red-400">
          ⚠️ {error}
        </div>
      )}

      {/* 생성 버튼 */}
      <button
        onClick={handleGenerate}
        disabled={isGenerating}
        className="w-full py-2.5 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
        title="Ctrl+G로 생성"
      >
        ✨ 챕터 생성
      </button>

      {/* 재생성 섹션 */}
      <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
          재생성 피드백
        </label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          disabled={isGenerating}
          placeholder="예: 톤을 더 밝게 조정해줘, 플롯을 다른 방향으로 전개해줘..."
          rows={2}
          className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none disabled:opacity-50"
        />
        <button
          onClick={handleRegenerate}
          disabled={isGenerating}
          className="w-full mt-2 py-2 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-sm rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          🔄 재생성
        </button>
      </div>

      {/* 단축키 안내 */}
      <div className="pt-4 border-t border-slate-200 dark:border-slate-700 text-xs text-slate-400 space-y-1">
        <p>
          <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-xs">
            Ctrl+S
          </kbd>{' '}
          저장
        </p>
        <p>
          <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-xs">
            Ctrl+G
          </kbd>{' '}
          생성
        </p>
        <p>
          <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-xs">
            Ctrl+N
          </kbd>{' '}
          새 챕터
        </p>
      </div>
    </div>
  )
}
