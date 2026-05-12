import { useEffect, useRef, useState } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import CharacterCount from '@tiptap/extension-character-count'

interface RichTextEditorProps {
  content: string
  title: string
  onContentChange: (content: string) => void
  onTitleChange: (title: string) => void
  saveStatus: 'saved' | 'saving' | 'unsaved'
}

export default function RichTextEditor({
  content,
  title,
  onContentChange,
  onTitleChange,
  saveStatus,
}: RichTextEditorProps) {
  const [wordCount, setWordCount] = useState(0)
  const autoSaveTimerRef = useRef<number | null>(null)

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      Placeholder.configure({
        placeholder: '여기에 소설 내용을 작성하거나 AI로 생성하세요...',
      }),
      CharacterCount,
    ],
    content,
    editorProps: {
      attributes: {
        class:
          'prose prose-slate dark:prose-invert max-w-none focus:outline-none min-h-[500px] px-8 py-6',
        style: 'line-height: 2; font-family: "Nanum Myeongjo", Georgia, serif;',
      },
    },
    onUpdate: ({ editor }) => {
      const html = editor.getHTML()
      const text = editor.getText()
      setWordCount(text.length)

      // 자동 저장 타이머 설정 (30초)
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current)
      }
      autoSaveTimerRef.current = setTimeout(() => {
        onContentChange(html)
      }, 30000)
    },
  })

  // 컨텐츠 변경 시 에디터 업데이트
  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content)
      setWordCount(editor.getText().length)
    }
  }, [content, editor])

  // 수동 저장 이벤트 리스너
  useEffect(() => {
    const handleSave = () => {
      if (editor) {
        onContentChange(editor.getHTML())
      }
    }

    window.addEventListener('editor:save', handleSave)
    return () => window.removeEventListener('editor:save', handleSave)
  }, [editor, onContentChange])

  // 컴포넌트 언마운트 시 자동 저장 타이머 정리
  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current)
      }
    }
  }, [])

  return (
    <div className="h-full flex flex-col bg-white dark:bg-slate-800">
      {/* 챕터 제목 */}
      <div className="border-b border-slate-200 dark:border-slate-700 px-6 py-3 flex items-center justify-between shrink-0">
        <input
          type="text"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="챕터 제목..."
          className="text-lg font-semibold bg-transparent text-slate-900 dark:text-white focus:outline-none placeholder-slate-300 dark:placeholder-slate-600 flex-1"
        />
        <div className="flex items-center gap-4 ml-4">
          {/* 글자 수 */}
          <span className="text-xs text-slate-400">
            {wordCount.toLocaleString()}자
          </span>
          {/* 저장 상태 */}
          <span
            className={`text-xs flex items-center gap-1.5 ${
              saveStatus === 'saved'
                ? 'text-green-500'
                : saveStatus === 'saving'
                ? 'text-yellow-500'
                : 'text-slate-400'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                saveStatus === 'saved'
                  ? 'bg-green-500'
                  : saveStatus === 'saving'
                  ? 'bg-yellow-500 animate-pulse'
                  : 'bg-slate-400'
              }`}
            />
            {saveStatus === 'saved'
              ? '저장됨'
              : saveStatus === 'saving'
              ? '저장 중...'
              : '미저장'}
          </span>
        </div>
      </div>

      {/* 에디터 툴바 */}
      {editor && (
        <div className="border-b border-slate-200 dark:border-slate-700 px-6 py-2 flex items-center gap-2 shrink-0">
          <button
            onClick={() => editor.chain().focus().toggleBold().run()}
            className={`px-2 py-1 text-sm rounded transition ${
              editor.isActive('bold')
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            <strong>B</strong>
          </button>
          <button
            onClick={() => editor.chain().focus().toggleItalic().run()}
            className={`px-2 py-1 text-sm rounded transition ${
              editor.isActive('italic')
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            <em>I</em>
          </button>
          <div className="w-px h-4 bg-slate-200 dark:bg-slate-700 mx-1" />
          <button
            onClick={() =>
              editor.chain().focus().toggleHeading({ level: 2 }).run()
            }
            className={`px-2 py-1 text-sm rounded transition ${
              editor.isActive('heading', { level: 2 })
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            H2
          </button>
          <button
            onClick={() =>
              editor.chain().focus().toggleHeading({ level: 3 }).run()
            }
            className={`px-2 py-1 text-sm rounded transition ${
              editor.isActive('heading', { level: 3 })
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            H3
          </button>
          <div className="w-px h-4 bg-slate-200 dark:bg-slate-700 mx-1" />
          <button
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            className={`px-2 py-1 text-sm rounded transition ${
              editor.isActive('bulletList')
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            • 목록
          </button>
          <button
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            className={`px-2 py-1 text-sm rounded transition ${
              editor.isActive('orderedList')
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            1. 목록
          </button>
          <div className="flex-1" />
          <span className="text-xs text-slate-400">
            Ctrl+S로 저장 • 30초마다 자동 저장
          </span>
        </div>
      )}

      {/* 에디터 컨텐츠 */}
      <div className="flex-1 overflow-y-auto">
        <EditorContent editor={editor} />
      </div>
    </div>
  )
}
