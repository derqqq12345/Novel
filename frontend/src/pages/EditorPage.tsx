import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  chaptersApi,
  charactersApi,
  plotApi,
  worldbuildingApi,
  consistencyApi,
  projectsApi,
} from '../api'
import EditorLayout from '../components/editor/EditorLayout'
import ChapterListPanel from '../components/editor/ChapterListPanel'
import RichTextEditor from '../components/editor/RichTextEditor'
import ChapterGenerationPanel, {
  GenerationParams,
} from '../components/editor/ChapterGenerationPanel'
import ContextSidebar from '../components/editor/ContextSidebar'
import CharacterList from '../components/characters/CharacterList'
import Button from '../components/ui/Button'
import Spinner from '../components/ui/Spinner'

type SidebarTab = 'generate' | 'characters'

export default function EditorPage() {
  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()
  const queryClient = useQueryClient()

  if (!projectId) {
    navigate('/dashboard')
    return null
  }

  // State
  const [selectedChapterId, setSelectedChapterId] = useState<string | null>(null)
  const [chapterTitle, setChapterTitle] = useState('')
  const [chapterContent, setChapterContent] = useState('')
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved')
  const [isGenerating, setIsGenerating] = useState(false)
  const [genProgress, setGenProgress] = useState(0)
  const [genError, setGenError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<SidebarTab>('generate')

  // Queries
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  })

  const { data: chaptersData, isLoading: chaptersLoading } = useQuery({
    queryKey: ['chapters', projectId],
    queryFn: () => chaptersApi.list(projectId),
  })

  const { data: charactersData } = useQuery({
    queryKey: ['characters', projectId],
    queryFn: () => charactersApi.list(projectId),
  })

  const { data: plotPointsData } = useQuery({
    queryKey: ['plot', projectId],
    queryFn: () => plotApi.list(projectId),
  })

  const { data: worldBuildingData } = useQuery({
    queryKey: ['worldbuilding', projectId],
    queryFn: () => worldbuildingApi.list(projectId),
  })

  // Ensure data is always an array
  const chapters = Array.isArray(chaptersData) ? chaptersData : []
  const characters = Array.isArray(charactersData) ? charactersData : []
  const plotPoints = Array.isArray(plotPointsData) ? plotPointsData : []
  const worldBuilding = Array.isArray(worldBuildingData) ? worldBuildingData : []

  // Debug: Log chapters data
  useEffect(() => {
    console.log('Raw chapters data:', chaptersData)
    console.log('Processed chapters:', chapters)
  }, [chaptersData, chapters])

  const { data: consistencyReport } = useQuery({
    queryKey: ['consistency', selectedChapterId],
    queryFn: () =>
      selectedChapterId ? consistencyApi.checkChapter(selectedChapterId) : null,
    enabled: !!selectedChapterId,
  })

  // Mutations
  const updateChapterMutation = useMutation({
    mutationFn: (data: { id: string; title?: string; content?: string }) =>
      chaptersApi.update(data.id, { title: data.title, content: data.content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapters', projectId] })
      setSaveStatus('saved')
    },
  })

  const deleteChapterMutation = useMutation({
    mutationFn: (chapterId: string) => chaptersApi.delete(chapterId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapters', projectId] })
    },
  })

  const reorderChaptersMutation = useMutation({
    mutationFn: (chapterIds: string[]) =>
      chaptersApi.reorder(projectId, chapterIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapters', projectId] })
    },
  })

  const regenerateChapterMutation = useMutation({
    mutationFn: (data: { chapterId: string; feedback?: string }) =>
      chaptersApi.regenerate(data.chapterId, data.feedback),
    onSuccess: (newChapter) => {
      queryClient.invalidateQueries({ queryKey: ['chapters', projectId] })
      setChapterContent(newChapter.content)
      setChapterTitle(newChapter.title || '')
    },
  })

  // Effects
  useEffect(() => {
    console.log('Chapters updated:', chapters.length, 'chapters')
    if (Array.isArray(chapters) && chapters.length > 0 && !selectedChapterId) {
      console.log('Auto-selecting first chapter:', chapters[0].id)
      setSelectedChapterId(chapters[0].id)
    }
  }, [chapters]) // selectedChapterId 제거 - 무한 루프 방지

  useEffect(() => {
    if (!Array.isArray(chapters)) return
    console.log('Selected chapter ID changed:', selectedChapterId)
    const selectedChapter = chapters.find((ch) => ch.id === selectedChapterId)
    if (selectedChapter) {
      console.log('Loading chapter content:', selectedChapter.title)
      setChapterTitle(selectedChapter.title || '')
      setChapterContent(selectedChapter.content)
      setSaveStatus('saved')
    }
  }, [selectedChapterId, chapters])

  // 새 챕터 추가 이벤트 리스너
  useEffect(() => {
    const handleNewChapter = () => {
      handleAddChapter()
    }
    window.addEventListener('editor:new-chapter', handleNewChapter)
    return () => window.removeEventListener('editor:new-chapter', handleNewChapter)
  }, [chapters])

  // Handlers
  const handleSelectChapter = (chapterId: string) => {
    if (saveStatus === 'unsaved') {
      handleSaveChapter()
    }
    setSelectedChapterId(chapterId)
  }

  const handleAddChapter = async () => {
    try {
      // 현재 챕터 저장
      if (selectedChapterId && saveStatus === 'unsaved') {
        await handleSaveChapter()
      }

      // 새 챕터 생성 (최소 내용 포함)
      const chapterCount = Array.isArray(chapters) ? chapters.length : 0
      console.log('Creating new chapter, current count:', chapterCount)
      
      const newChapter = await chaptersApi.create(projectId, {
        title: `챕터 ${chapterCount + 1}`,
        content: ' ', // 최소 1자 필요 (빈 공백)
      })
      
      console.log('New chapter created:', newChapter)
      
      // 챕터 목록 새로고침
      await queryClient.invalidateQueries({ queryKey: ['chapters', projectId] })
      
      // 새 챕터 선택
      setSelectedChapterId(newChapter.id)
      console.log('Selected new chapter:', newChapter.id)
    } catch (error) {
      console.error('Failed to create chapter:', error)
      setGenError(error instanceof Error ? error.message : '챕터 생성 실패')
    }
  }

  const handleDeleteChapter = (chapterId: string) => {
    deleteChapterMutation.mutate(chapterId)
    if (selectedChapterId === chapterId) {
      const remainingChapters = Array.isArray(chapters) 
        ? chapters.filter((ch) => ch.id !== chapterId)
        : []
      setSelectedChapterId(remainingChapters[0]?.id || null)
    }
  }

  const handleReorderChapters = (chapterIds: string[]) => {
    reorderChaptersMutation.mutate(chapterIds)
  }

  const handleContentChange = (content: string) => {
    setChapterContent(content)
    setSaveStatus('unsaved')
  }

  const handleTitleChange = (title: string) => {
    setChapterTitle(title)
    setSaveStatus('unsaved')
  }

  const handleSaveChapter = async () => {
    if (!selectedChapterId) return
    setSaveStatus('saving')
    await updateChapterMutation.mutateAsync({
      id: selectedChapterId,
      title: chapterTitle,
      content: chapterContent,
    })
  }

  const handleGenerate = async (params: GenerationParams) => {
    setIsGenerating(true)
    setGenProgress(0)
    setGenError(null)

    try {
      const chapterCount = Array.isArray(chapters) ? chapters.length : 0
      
      // Get previous chapter content for context
      const previousContent = chapterCount > 0 && chapters[chapterCount - 1]
        ? chapters[chapterCount - 1].content
        : undefined

      // Call the streaming generate API endpoint
      const response = await fetch(`/api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          genre: params.genre,
          tone: params.tone,
          temperature: params.temperature,
          chapter_number: chapterCount + 1,
          previous_content: previousContent,
          user_prompt: params.userPrompt,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || '생성 실패')
      }

      // Handle SSE streaming response
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let generatedText = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') {
                break
              }
              try {
                const parsed = JSON.parse(data)
                if (parsed.error) {
                  throw new Error(parsed.error)
                }
                if (parsed.text) {
                  generatedText += parsed.text
                  // Update progress based on text length (rough estimate)
                  const progress = Math.min(95, (generatedText.length / 2000) * 100)
                  setGenProgress(progress)
                }
              } catch (e) {
                // Skip invalid JSON
              }
            }
          }
        }
      }

      // Save generated content as a new chapter
      // Don't specify chapter_number - let backend auto-assign to avoid conflicts
      const newChapter = await chaptersApi.create(projectId, {
        title: `챕터 ${chapterCount + 1}`,
        content: generatedText,
        word_count: generatedText.length,
      })

      queryClient.invalidateQueries({ queryKey: ['chapters', projectId] })
      setSelectedChapterId(newChapter.id)
      setGenProgress(100)
    } catch (error) {
      setGenError(error instanceof Error ? error.message : '알 수 없는 오류')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleRegenerate = (feedback: string) => {
    if (!selectedChapterId) return
    regenerateChapterMutation.mutate({ chapterId: selectedChapterId, feedback })
  }

  if (chaptersLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Spinner />
      </div>
    )
  }

  const selectedChapter = Array.isArray(chapters) 
    ? chapters.find((ch) => ch.id === selectedChapterId)
    : undefined

  return (
    <EditorLayout
      header={
        <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-4 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/dashboard')}
              className="text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 text-sm flex items-center gap-1"
            >
              ← 대시보드
            </button>
            <span className="text-slate-300 dark:text-slate-600">|</span>
            <span className="font-semibold text-slate-900 dark:text-white text-sm">
              {project?.title || '프로젝트'}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => navigate(`/projects/${projectId}/export`)}
            >
              내보내기
            </Button>
          </div>
        </header>
      }
      chapterList={
        <ChapterListPanel
          chapters={chapters}
          selectedChapterId={selectedChapterId}
          onSelectChapter={handleSelectChapter}
          onAddChapter={handleAddChapter}
          onDeleteChapter={handleDeleteChapter}
          onReorderChapters={handleReorderChapters}
        />
      }
      editor={
        selectedChapter ? (
          <RichTextEditor
            content={chapterContent}
            title={chapterTitle}
            onContentChange={handleContentChange}
            onTitleChange={handleTitleChange}
            saveStatus={saveStatus}
          />
        ) : (
          <div className="h-full flex items-center justify-center text-slate-400">
            챕터를 선택하거나 새로 추가하세요
          </div>
        )
      }
      contextSidebar={
        <div className="h-full flex flex-col">
          {/* 탭 헤더 */}
          <div className="flex border-b border-slate-200 dark:border-slate-700 shrink-0">
            <button
              onClick={() => setActiveTab('generate')}
              className={`flex-1 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                activeTab === 'generate'
                  ? 'text-primary-600 dark:text-primary-400 border-primary-600'
                  : 'text-gray-500 dark:text-gray-400 border-transparent hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              생성
            </button>
            <button
              onClick={() => setActiveTab('characters')}
              className={`flex-1 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                activeTab === 'characters'
                  ? 'text-primary-600 dark:text-primary-400 border-primary-600'
                  : 'text-gray-500 dark:text-gray-400 border-transparent hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              캐릭터
            </button>
          </div>
          
          {/* 탭 컨텐츠 */}
          <div className="flex-1 overflow-y-auto p-4">
            {activeTab === 'generate' && (
              <ChapterGenerationPanel
                projectId={projectId}
                onGenerate={handleGenerate}
                onRegenerate={handleRegenerate}
                isGenerating={isGenerating}
                progress={genProgress}
                error={genError}
              />
            )}
            {activeTab === 'characters' && (
              <CharacterList projectId={projectId} characters={characters} />
            )}
          </div>
        </div>
      }
    />
  )
}
