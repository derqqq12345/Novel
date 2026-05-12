import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { charactersApi, projectsApi } from '../api'
import CharacterList from '../components/characters/CharacterList'
import Button from '../components/ui/Button'
import Spinner from '../components/ui/Spinner'

export default function CharactersPage() {
  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()

  if (!projectId) {
    navigate('/dashboard')
    return null
  }

  // Queries
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  })

  const { data: charactersData, isLoading } = useQuery({
    queryKey: ['characters', projectId],
    queryFn: () => charactersApi.list(projectId),
  })

  const characters = Array.isArray(charactersData) ? charactersData : []

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* 헤더 */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(`/projects/${projectId}/editor`)}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 text-sm flex items-center gap-1"
            >
              ← 에디터로 돌아가기
            </button>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span className="font-semibold text-gray-900 dark:text-white">
              {project?.title || '프로젝트'} - 캐릭터 관리
            </span>
          </div>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => navigate('/dashboard')}
          >
            대시보드
          </Button>
        </div>
      </header>

      {/* 메인 컨텐츠 */}
      <main className="flex-1 overflow-hidden p-6">
        <div className="h-full max-w-7xl mx-auto">
          <CharacterList projectId={projectId} characters={characters} />
        </div>
      </main>
    </div>
  )
}
