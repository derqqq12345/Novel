import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useProjects } from '../hooks/useProjects'
import { GENRE_LABELS, type Genre, type ProjectCreate } from '../types'
import { Spinner } from '../components/ui'

interface NewProjectModal {
  title: string
  genre: Genre
  description: string
}

type SortOption = 'date' | 'title' | 'chapters' | 'words'

export default function DashboardPage() {
  const navigate = useNavigate()
  const [showModal, setShowModal] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<SortOption>('date')
  const [form, setForm] = useState<NewProjectModal>({ 
    title: '', 
    genre: 'fantasy', 
    description: '' 
  })

  // Use the real API hook
  const { 
    projects, 
    isLoading, 
    error, 
    createProject, 
    deleteProject, 
    isCreating, 
    isDeleting 
  } = useProjects()

  // Filter and sort projects
  const filteredAndSorted = useMemo(() => {
    let filtered = projects.filter((p) =>
      p.title.toLowerCase().includes(search.toLowerCase()),
    )

    // Sort based on selected option
    switch (sortBy) {
      case 'title':
        filtered = [...filtered].sort((a, b) => a.title.localeCompare(b.title))
        break
      case 'chapters':
        filtered = [...filtered].sort((a, b) => (b.chapter_count ?? 0) - (a.chapter_count ?? 0))
        break
      case 'words':
        filtered = [...filtered].sort((a, b) => b.total_word_count - a.total_word_count)
        break
      case 'date':
      default:
        filtered = [...filtered].sort((a, b) => 
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        )
        break
    }

    return filtered
  }, [projects, search, sortBy])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!form.title.trim()) {
      alert('제목을 입력해주세요')
      return
    }

    try {
      const projectData: ProjectCreate = {
        title: form.title,
        genre: form.genre,
        description: form.description || undefined,
      }
      
      await createProject(projectData)
      setShowModal(false)
      setForm({ title: '', genre: 'fantasy', description: '' })
    } catch (err) {
      console.error('Failed to create project:', err)
      alert('프로젝트 생성에 실패했습니다. 다시 시도해주세요.')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteProject(id)
      setDeleteTarget(null)
    } catch (err) {
      console.error('Failed to delete project:', err)
      alert('프로젝트 삭제에 실패했습니다. 다시 시도해주세요.')
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* 헤더 */}
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-sm">✍️</span>
            </div>
            <span className="font-bold text-slate-900 dark:text-white text-lg">AI 소설 플랫폼</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-500 dark:text-slate-400">데모 사용자</span>
            <button
              onClick={() => navigate('/login')}
              className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            >
              로그아웃
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* 상단 타이틀 + 검색 + 정렬 + 생성 버튼 */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">내 소설 프로젝트</h2>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">총 {projects.length}개의 프로젝트</p>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="프로젝트 검색..."
              className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 w-48"
            />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="date">최근 수정순</option>
              <option value="title">제목순</option>
              <option value="chapters">챕터순</option>
              <option value="words">글자수순</option>
            </select>
            <button
              onClick={() => setShowModal(true)}
              disabled={isCreating}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition flex items-center gap-2"
            >
              {isCreating ? <Spinner size="sm" /> : <span>+</span>} 새 프로젝트
            </button>
          </div>
        </div>

        {/* 로딩 상태 */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Spinner size="lg" />
          </div>
        )}

        {/* 에러 상태 */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
            <p className="text-red-800 dark:text-red-200 text-sm">
              프로젝트를 불러오는데 실패했습니다. 다시 시도해주세요.
            </p>
          </div>
        )}

        {/* 프로젝트 그리드 */}
        {!isLoading && !error && filteredAndSorted.length === 0 && (
          <div className="text-center py-20 text-slate-400">
            <p className="text-4xl mb-4">📚</p>
            <p className="text-lg font-medium">
              {search ? '검색 결과가 없습니다' : '프로젝트가 없습니다'}
            </p>
            <p className="text-sm mt-1">
              {search ? '다른 검색어를 시도해보세요' : '새 프로젝트를 만들어 소설을 시작해보세요'}
            </p>
          </div>
        )}

        {!isLoading && !error && filteredAndSorted.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredAndSorted.map((project) => (
              <div
                key={project.id}
                className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 hover:shadow-md transition cursor-pointer group"
                onClick={() => navigate(`/editor/${project.id}`)}
              >
                {/* 장르 배지 */}
                <div className="flex items-start justify-between mb-3">
                  <span className="px-2.5 py-1 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-xs font-medium rounded-full">
                    {project.genre ? GENRE_LABELS[project.genre] : '미분류'}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleteTarget(project.id)
                    }}
                    disabled={isDeleting}
                    className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 disabled:text-slate-300 transition text-lg leading-none"
                  >
                    ×
                  </button>
                </div>

                {/* 제목 */}
                <h3 className="font-bold text-slate-900 dark:text-white text-lg mb-3 line-clamp-2">
                  {project.title}
                </h3>

                {/* 통계 */}
                <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
                  <span>📖 {project.chapter_count ?? 0}챕터</span>
                  <span>✏️ {project.total_word_count.toLocaleString()}자</span>
                </div>

                <p className="text-xs text-slate-400 dark:text-slate-500 mt-3">
                  {new Date(project.updated_at).toLocaleDateString('ko-KR')} 수정
                </p>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* 새 프로젝트 모달 */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md p-6">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-5">새 프로젝트 만들기</h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">제목 *</label>
                <input
                  type="text"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="소설 제목을 입력하세요"
                  required
                  className="w-full px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">장르</label>
                <select
                  value={form.genre}
                  onChange={(e) => setForm({ ...form, genre: e.target.value as Genre })}
                  className="w-full px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {Object.entries(GENRE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">설명 (선택)</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="소설에 대한 간단한 설명..."
                  rows={3}
                  className="w-full px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  disabled={isCreating}
                  className="flex-1 py-2.5 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  취소
                </button>
                <button
                  type="submit"
                  disabled={isCreating || !form.title.trim()}
                  className="flex-1 py-2.5 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition flex items-center justify-center gap-2"
                >
                  {isCreating ? (
                    <>
                      <Spinner size="sm" />
                      <span>생성 중...</span>
                    </>
                  ) : (
                    '만들기'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 삭제 확인 다이얼로그 */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-sm p-6 text-center">
            <p className="text-4xl mb-4">🗑️</p>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">프로젝트 삭제</h3>
            <p className="text-slate-500 dark:text-slate-400 text-sm mb-6">
              이 프로젝트를 삭제하면 모든 챕터가 함께 삭제됩니다. 계속하시겠습니까?
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={isDeleting}
                className="flex-1 py-2.5 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                취소
              </button>
              <button
                onClick={() => handleDelete(deleteTarget)}
                disabled={isDeleting}
                className="flex-1 py-2.5 bg-red-500 hover:bg-red-600 disabled:bg-red-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition flex items-center justify-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <Spinner size="sm" />
                    <span>삭제 중...</span>
                  </>
                ) : (
                  '삭제'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
