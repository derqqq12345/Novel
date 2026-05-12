import { ReactNode, useEffect } from 'react'

interface EditorLayoutProps {
  header: ReactNode
  chapterList: ReactNode
  editor: ReactNode
  contextSidebar: ReactNode
}

export default function EditorLayout({
  header,
  chapterList,
  editor,
  contextSidebar,
}: EditorLayoutProps) {
  // 키보드 단축키 설정
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+S: 저장
      if (e.ctrlKey && e.key === 's') {
        e.preventDefault()
        const event = new CustomEvent('editor:save')
        window.dispatchEvent(event)
      }
      // Ctrl+G: 생성
      if (e.ctrlKey && e.key === 'g') {
        e.preventDefault()
        const event = new CustomEvent('editor:generate')
        window.dispatchEvent(event)
      }
      // Ctrl+N: 새 챕터
      if (e.ctrlKey && e.key === 'n') {
        e.preventDefault()
        const event = new CustomEvent('editor:new-chapter')
        window.dispatchEvent(event)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div className="h-screen flex flex-col bg-slate-50 dark:bg-slate-900 overflow-hidden">
      {/* 헤더 */}
      {header}

      {/* 3단 레이아웃 */}
      <div className="flex flex-1 overflow-hidden">
        {/* 좌측: 챕터 목록 (최소 768px에서 표시) */}
        <aside className="hidden md:block w-64 lg:w-72 shrink-0">
          {chapterList}
        </aside>

        {/* 중앙: 에디터 */}
        <main className="flex-1 overflow-hidden">{editor}</main>

        {/* 우측: 컨텍스트 패널 (최소 768px에서 표시) */}
        <aside className="hidden md:block w-72 lg:w-80 shrink-0">
          {contextSidebar}
        </aside>
      </div>
    </div>
  )
}
