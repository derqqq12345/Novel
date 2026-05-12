import { DragDropContext, Droppable, Draggable, DropResult } from 'react-beautiful-dnd'
import type { Chapter } from '../../types'

interface ChapterListPanelProps {
  chapters: Chapter[]
  selectedChapterId: string | null
  onSelectChapter: (chapterId: string) => void
  onAddChapter: () => void
  onDeleteChapter: (chapterId: string) => void
  onReorderChapters: (chapterIds: string[]) => void
}

export default function ChapterListPanel({
  chapters,
  selectedChapterId,
  onSelectChapter,
  onAddChapter,
  onDeleteChapter,
  onReorderChapters,
}: ChapterListPanelProps) {
  const handleDragEnd = (result: DropResult) => {
    if (!result.destination) return

    const items = Array.from(chapters)
    const [reorderedItem] = items.splice(result.source.index, 1)
    items.splice(result.destination.index, 0, reorderedItem)

    const reorderedIds = items.map((ch) => ch.id)
    onReorderChapters(reorderedIds)
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('ko-KR', {
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <div className="h-full bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 flex flex-col">
      {/* 헤더 */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between shrink-0">
        <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">
          챕터 목록
        </span>
        <button
          onClick={onAddChapter}
          className="w-7 h-7 bg-primary-600 hover:bg-primary-700 text-white rounded-lg flex items-center justify-center text-lg transition"
          title="새 챕터 추가 (Ctrl+N)"
        >
          +
        </button>
      </div>

      {/* 챕터 목록 (드래그 앤 드롭) */}
      <div className="flex-1 overflow-y-auto p-2">
        <DragDropContext onDragEnd={handleDragEnd}>
          <Droppable droppableId="chapters">
            {(provided) => (
              <div
                {...provided.droppableProps}
                ref={provided.innerRef}
                className="space-y-1"
              >
                {chapters.map((chapter, index) => (
                  <Draggable
                    key={chapter.id}
                    draggableId={chapter.id}
                    index={index}
                  >
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        {...provided.dragHandleProps}
                        onClick={() => onSelectChapter(chapter.id)}
                        className={`p-3 rounded-lg cursor-pointer group transition ${
                          snapshot.isDragging
                            ? 'shadow-lg bg-primary-100 dark:bg-primary-900/50'
                            : selectedChapterId === chapter.id
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
                              {chapter.title || `챕터 ${chapter.chapter_number}`}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              <p className="text-xs text-slate-400 dark:text-slate-500">
                                {chapter.word_count.toLocaleString()}자
                              </p>
                              <span className="text-xs text-slate-300 dark:text-slate-600">
                                •
                              </span>
                              <p className="text-xs text-slate-400 dark:text-slate-500">
                                {formatDate(chapter.created_at)}
                              </p>
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-1 ml-2">
                            {chapter.consistency_score != null && (
                              <span
                                className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                                  chapter.consistency_score >= 90
                                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                    : chapter.consistency_score >= 70
                                    ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                                    : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                }`}
                              >
                                {chapter.consistency_score}
                              </span>
                            )}
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                if (
                                  window.confirm(
                                    `"${chapter.title || `챕터 ${chapter.chapter_number}`}"을(를) 삭제하시겠습니까?`
                                  )
                                ) {
                                  onDeleteChapter(chapter.id)
                                }
                              }}
                              className="opacity-0 group-hover:opacity-100 text-slate-300 hover:text-red-500 transition text-lg leading-none"
                            >
                              ×
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
              </div>
            )}
          </Droppable>
        </DragDropContext>

        {chapters.length === 0 && (
          <div className="text-center py-8 text-slate-400 dark:text-slate-500 text-sm">
            챕터가 없습니다.
            <br />
            <button
              onClick={onAddChapter}
              className="text-primary-600 hover:text-primary-700 mt-2"
            >
              + 첫 챕터 추가
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
