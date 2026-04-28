import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const API_BASE = '/api'

const DEMO_CHAPTERS: Chapter[] = [
  { id: '1', chapter_number: 1, title: '운명의 시작', word_count: 3200, consistency_score: 92 },
  { id: '2', chapter_number: 2, title: '어둠 속의 빛', word_count: 4100, consistency_score: 88 },
  { id: '3', chapter_number: 3, title: '배신의 그림자', word_count: 3800, consistency_score: 95 },
]

interface Chapter {
  id: string
  chapter_number: number
  title: string
  word_count: number
  consistency_score: number | null
}

const DEMO_CONTENT = `하늘이 붉게 물들던 그날 저녁, 이준혁은 처음으로 그 검은 기사를 보았다.

성벽 위에서 바라본 기사의 갑옷은 마치 밤하늘을 담은 듯 깊고 어두운 빛을 발하고 있었다. 말 위에 올라탄 그의 자태는 위엄 그 자체였으며, 주변의 공기마저 그를 중심으로 응집되는 것 같았다.

"저 자가 바로 어둠의 기사단 단장이오."

옆에 서 있던 노장 기사 박철수가 낮은 목소리로 속삭였다. 그의 목소리에는 경외와 두려움이 뒤섞여 있었다.

이준혁은 눈을 가늘게 뜨며 기사를 바라보았다. 전설 속에서만 듣던 존재가 이제 눈앞에 실재하고 있었다. 심장이 빠르게 뛰기 시작했다.`

const DEMO_CHARACTERS = [
  { id: '1', name: '이준혁', age: 24, personality_traits: ['용감함', '정의로움'] },
  { id: '2', name: '박철수', age: 58, personality_traits: ['노련함', '신중함'] },
  { id: '3', name: '어둠의 기사', age: null, personality_traits: ['신비로움', '강인함'] },
]

const DEMO_PLOT = [
  { id: '1', title: '주인공의 각성', plot_stage: 'exposition', is_completed: true },
  { id: '2', title: '기사단과의 첫 만남', plot_stage: 'rising_action', is_completed: true },
  { id: '3', title: '배신자의 등장', plot_stage: 'rising_action', is_completed: false },
  { id: '4', title: '최후의 결전', plot_stage: 'climax', is_completed: false },
]

const PLOT_STAGE_LABELS: Record<string, string> = {
  exposition: '발단',
  rising_action: '전개',
  climax: '절정',
  falling_action: '하강',
  resolution: '결말',
}

type SidebarTab = 'generate' | 'characters' | 'plot' | 'worldbuilding'

export default function EditorPage() {
  const navigate = useNavigate()

  const [chapters, setChapters] = useState<Chapter[]>(DEMO_CHAPTERS)
  const [selectedChapterId, setSelectedChapterId] = useState('1')
  const [content, setContent] = useState(DEMO_CONTENT)
  const [sidebarTab, setSidebarTab] = useState<SidebarTab>('generate')
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved')
  const [isGenerating, setIsGenerating] = useState(false)
  const [genProgress, setGenProgress] = useState(0)
  const [genError, setGenError] = useState('')
  const [ollamaOk, setOllamaOk] = useState<boolean | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Ollama 연결 상태 확인
  useEffect(() => {
    fetch(`${API_BASE}/generate/health`)
      .then((r) => setOllamaOk(r.ok))
      .catch(() => setOllamaOk(false))
  }, [])
  const [tone, setTone] = useState('serious')
  const [temperature, setTemperature] = useState(0.7)
  const [userPrompt, setUserPrompt] = useState('')

  const selectedChapter = chapters.find((c) => c.id === selectedChapterId)

  // 데모: 저장 시뮬레이션
  const handleContentChange = (val: string) => {
    setContent(val)
    setSaveStatus('unsaved')
    setTimeout(() => setSaveStatus('saving'), 500)
    setTimeout(() => setSaveStatus('saved'), 1500)
  }

  // 실제 Qwen API 스트리밍 생성
  const handleGenerate = async () => {
    setIsGenerating(true)
    setGenProgress(0)
    setGenError('')

    // 새 챕터 슬롯 추가
    const newChapter: Chapter = {
      id: String(Date.now()),
      chapter_number: chapters.length + 1,
      title: `챕터 ${chapters.length + 1}`,
      word_count: 0,
      consistency_score: null,
    }
    setChapters((prev) => [...prev, newChapter])
    setSelectedChapterId(newChapter.id)
    setContent('')

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const response = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          genre: 'fantasy',
          tone,
          temperature,
          chapter_number: newChapter.chapter_number,
          previous_content: content || undefined,
          user_prompt: userPrompt || undefined,
        }),
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail ?? '생성 실패')
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''
      let streamError = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data:')) continue
          const data = line.slice(5).trim()
          if (data === '[DONE]') break

          try {
            const parsed = JSON.parse(data)
            if (parsed.error) {
              streamError = parsed.error
              break
            }
            if (parsed.text) {
              accumulated += parsed.text
              setContent(accumulated)
              setGenProgress(Math.min(Math.floor((accumulated.length / 2000) * 100), 95))
            }
          } catch {
            // JSON 파싱 실패는 무시
          }
        }

        if (streamError) break
      }

      if (streamError) {
        throw new Error(streamError)
      }

      // 완료
      setGenProgress(100)
      setChapters((prev) =>
        prev.map((c) =>
          c.id === newChapter.id
            ? { ...c, word_count: accumulated.length }
            : c,
        ),
      )
    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') return
      const msg = err instanceof Error ? err.message : '알 수 없는 오류'
      console.error('생성 에러:', err)
      setGenError(msg)
      // 실패한 챕터 제거
      setChapters((prev) => prev.filter((c) => c.id !== newChapter.id))
      setSelectedChapterId(chapters[chapters.length - 1]?.id ?? '')
    } finally {
      setIsGenerating(false)
      abortRef.current = null
    }
  }

  const handleStopGenerate = () => {
    abortRef.current?.abort()
    setIsGenerating(false)
  }

  const handleDeleteChapter = (id: string) => {
    setChapters(chapters.filter((c) => c.id !== id))
    if (selectedChapterId === id) {
      setSelectedChapterId(chapters[0]?.id ?? '')
    }
  }

  return (
    <div className="h-screen flex flex-col bg-slate-50 dark:bg-slate-900 overflow-hidden">
      {/* 상단 헤더 */}
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 text-sm flex items-center gap-1"
          >
            ← 대시보드
          </button>
          <span className="text-slate-300 dark:text-slate-600">|</span>
          <span className="font-semibold text-slate-900 dark:text-white text-sm">어둠의 기사단</span>
        </div>
        <div className="flex items-center gap-3">
          {/* 저장 상태 */}
          <span className={`text-xs flex items-center gap-1.5 ${
            saveStatus === 'saved' ? 'text-green-500' :
            saveStatus === 'saving' ? 'text-yellow-500' : 'text-slate-400'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${
              saveStatus === 'saved' ? 'bg-green-500' :
              saveStatus === 'saving' ? 'bg-yellow-500 animate-pulse' : 'bg-slate-400'
            }`} />
            {saveStatus === 'saved' ? '저장됨' : saveStatus === 'saving' ? '저장 중...' : '미저장'}
          </span>
          <button className="px-3 py-1.5 text-sm border border-slate-200 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition">
            내보내기
          </button>
        </div>
      </header>

      {/* 3단 레이아웃 */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── 좌측: 챕터 목록 ── */}
        <aside className="w-64 bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 flex flex-col shrink-0">
          <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">챕터 목록</span>
            <button
              onClick={() => {
                const newChapter = {
                  id: String(Date.now()),
                  chapter_number: chapters.length + 1,
                  title: `챕터 ${chapters.length + 1}`,
                  word_count: 0,
                  consistency_score: null,
                }
                setChapters([...chapters, newChapter as typeof chapters[0]])
                setSelectedChapterId(newChapter.id)
                setContent('')
              }}
              className="w-6 h-6 bg-primary-600 hover:bg-primary-700 text-white rounded flex items-center justify-center text-sm transition"
            >
              +
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {chapters.map((chapter) => (
              <div
                key={chapter.id}
                onClick={() => setSelectedChapterId(chapter.id)}
                className={`p-3 rounded-lg cursor-pointer group transition ${
                  selectedChapterId === chapter.id
                    ? 'bg-primary-50 dark:bg-primary-900/30 border border-primary-200 dark:border-primary-700'
                    : 'hover:bg-slate-50 dark:hover:bg-slate-700'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">
                      챕터 {chapter.chapter_number}
                    </p>
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                      {chapter.title}
                    </p>
                    <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                      {chapter.word_count.toLocaleString()}자
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-1 ml-2">
                    {chapter.consistency_score != null && (
                      <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                        chapter.consistency_score >= 90 ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                        chapter.consistency_score >= 70 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                        'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      }`}>
                        {chapter.consistency_score}
                      </span>
                    )}
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteChapter(chapter.id) }}
                      className="opacity-0 group-hover:opacity-100 text-slate-300 hover:text-red-500 transition text-base leading-none"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* ── 중앙: 에디터 ── */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* 챕터 제목 */}
          <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-3 flex items-center justify-between shrink-0">
            <input
              type="text"
              defaultValue={selectedChapter?.title ?? ''}
              key={selectedChapterId}
              placeholder="챕터 제목..."
              className="text-lg font-semibold bg-transparent text-slate-900 dark:text-white focus:outline-none placeholder-slate-300 flex-1"
            />
            <span className="text-xs text-slate-400 ml-4">
              {content.length.toLocaleString()}자
            </span>
          </div>

          {/* 텍스트 에디터 */}
          <div className="flex-1 overflow-y-auto bg-white dark:bg-slate-800 px-8 py-6">
            <textarea
              value={content}
              onChange={(e) => handleContentChange(e.target.value)}
              placeholder="여기에 소설 내용을 작성하거나 AI로 생성하세요..."
              className="w-full h-full min-h-[500px] bg-transparent text-slate-800 dark:text-slate-200 text-base leading-8 font-serif resize-none focus:outline-none placeholder-slate-300 dark:placeholder-slate-600"
              style={{ lineHeight: '2' }}
            />
          </div>
        </main>

        {/* ── 우측: 컨텍스트 패널 ── */}
        <aside className="w-72 bg-white dark:bg-slate-800 border-l border-slate-200 dark:border-slate-700 flex flex-col shrink-0">
          {/* 탭 */}
          <div className="flex border-b border-slate-200 dark:border-slate-700 shrink-0">
            {(['generate', 'characters', 'plot', 'worldbuilding'] as SidebarTab[]).map((tab) => {
              const labels = { generate: '생성', characters: '캐릭터', plot: '플롯', worldbuilding: '세계관' }
              return (
                <button
                  key={tab}
                  onClick={() => setSidebarTab(tab)}
                  className={`flex-1 py-2.5 text-xs font-medium transition ${
                    sidebarTab === tab
                      ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-600'
                      : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                  }`}
                >
                  {labels[tab]}
                </button>
              )
            })}
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {/* 생성 탭 */}
            {sidebarTab === 'generate' && (
              <div className="space-y-4">
                {/* Ollama 연결 상태 */}
                {ollamaOk === false && (
                  <div className="px-3 py-2 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg text-xs text-amber-700 dark:text-amber-300">
                    ⚠️ Ollama 연결 안 됨. <code className="bg-amber-100 dark:bg-amber-900 px-1 rounded">ollama serve</code> 실행 확인
                  </div>
                )}
                {ollamaOk === true && (
                  <div className="px-3 py-2 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg text-xs text-green-700 dark:text-green-300 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                    Ollama 연결됨 (qwen2.5:14b)
                  </div>
                )}

                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">톤</label>
                  <select
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="serious">진지함</option>
                    <option value="humorous">유머러스</option>
                    <option value="dark">어두움</option>
                    <option value="lighthearted">가벼움</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
                    창의성 <span className="text-primary-500">{temperature.toFixed(1)}</span>
                  </label>
                  <input
                    type="range"
                    min="0.3"
                    max="1.2"
                    step="0.1"
                    value={temperature}
                    onChange={(e) => setTemperature(Number(e.target.value))}
                    className="w-full accent-primary-600"
                  />
                  <div className="flex justify-between text-xs text-slate-400 mt-1">
                    <span>일관적</span>
                    <span>창의적</span>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">추가 지시사항</label>
                  <textarea
                    value={userPrompt}
                    onChange={(e) => setUserPrompt(e.target.value)}
                    placeholder="예: 주인공이 적과 처음 대면하는 장면을 써줘..."
                    rows={3}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                  />
                </div>

                {/* 생성 진행 바 */}
                {isGenerating && (
                  <div>
                    <div className="flex justify-between text-xs text-slate-500 mb-1">
                      <span>생성 중... (실시간 스트리밍)</span>
                      <span>{genProgress}%</span>
                    </div>
                    <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                      <div
                        className="bg-primary-600 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${genProgress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* 에러 메시지 */}
                {genError && (
                  <div className="px-3 py-2 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-600 dark:text-red-400">
                    ⚠️ {genError}
                  </div>
                )}

                {isGenerating ? (
                  <button
                    onClick={handleStopGenerate}
                    className="w-full py-2.5 bg-red-500 hover:bg-red-600 text-white text-sm font-medium rounded-lg transition"
                  >
                    ⏹ 생성 중지
                  </button>
                ) : (
                  <button
                    onClick={handleGenerate}
                    className="w-full py-2.5 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition"
                  >
                    ✨ 챕터 생성
                  </button>
                )}
                <button
                  onClick={() => {
                    setUserPrompt('')
                    handleGenerate()
                  }}
                  disabled={isGenerating}
                  className="w-full py-2 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-sm rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition"
                >
                  🔄 재생성
                </button>
              </div>
            )}

            {/* 캐릭터 탭 */}
            {sidebarTab === 'characters' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">등장인물</span>
                  <button className="text-xs text-primary-600 hover:text-primary-700">+ 추가</button>
                </div>
                {DEMO_CHARACTERS.map((char) => (
                  <div key={char.id} className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-slate-800 dark:text-slate-200">{char.name}</span>
                      {char.age && <span className="text-xs text-slate-400">{char.age}세</span>}
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {char.personality_traits.map((trait) => (
                        <span key={trait} className="text-xs px-2 py-0.5 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full">
                          {trait}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* 플롯 탭 */}
            {sidebarTab === 'plot' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">플롯 구조</span>
                  <button className="text-xs text-primary-600 hover:text-primary-700">+ 추가</button>
                </div>
                {DEMO_PLOT.map((point) => (
                  <div key={point.id} className={`p-3 rounded-lg border ${
                    point.is_completed
                      ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                      : 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600'
                  }`}>
                    <div className="flex items-start gap-2">
                      <span className={`mt-0.5 text-sm ${point.is_completed ? 'text-green-500' : 'text-slate-300'}`}>
                        {point.is_completed ? '✓' : '○'}
                      </span>
                      <div>
                        <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{point.title}</p>
                        <p className="text-xs text-slate-400 mt-0.5">{PLOT_STAGE_LABELS[point.plot_stage]}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* 세계관 탭 */}
            {sidebarTab === 'worldbuilding' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">세계관 설정</span>
                  <button className="text-xs text-primary-600 hover:text-primary-700">+ 추가</button>
                </div>
                {[
                  { name: '왕도 아르카나', category: '장소', desc: '왕국의 수도. 높은 성벽으로 둘러싸인 거대한 도시.' },
                  { name: '어둠의 마법', category: '마법 체계', desc: '감정을 에너지원으로 사용하는 금지된 마법.' },
                  { name: '기사단 서열', category: '문화', desc: '1~10등급으로 나뉘며 등급에 따라 권한이 다름.' },
                ].map((item) => (
                  <div key={item.name} className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-slate-800 dark:text-slate-200">{item.name}</span>
                      <span className="text-xs px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-full">{item.category}</span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{item.desc}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 일관성 점수 (하단 고정) */}
          <div className="p-4 border-t border-slate-200 dark:border-slate-700 shrink-0">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-400">일관성 점수</span>
              <span className="text-sm font-bold text-green-600 dark:text-green-400">
                {selectedChapter?.consistency_score ?? '-'}
              </span>
            </div>
            <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5">
              <div
                className="bg-green-500 h-1.5 rounded-full"
                style={{ width: `${selectedChapter?.consistency_score ?? 0}%` }}
              />
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
