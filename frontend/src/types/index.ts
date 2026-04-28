// ─── 공통 ─────────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

export interface ApiError {
  detail: string
  status_code?: number
}

// ─── 사용자 ───────────────────────────────────────────────────────────────────

export interface User {
  id: string
  email: string
  username: string
  created_at: string
  is_active: boolean
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

// ─── 프로젝트 ─────────────────────────────────────────────────────────────────

export type Genre = 'fantasy' | 'romance' | 'mystery' | 'science_fiction' | 'thriller'
export type ProjectStatus = 'active' | 'completed' | 'archived'

export const GENRE_LABELS: Record<Genre, string> = {
  fantasy: '판타지',
  romance: '로맨스',
  mystery: '미스터리',
  science_fiction: 'SF',
  thriller: '스릴러',
}

export interface Project {
  id: string
  user_id: string
  title: string
  genre: Genre | null
  description: string | null
  created_at: string
  updated_at: string
  total_word_count: number
  status: ProjectStatus
  chapter_count?: number
}

export interface ProjectCreate {
  title: string
  genre?: Genre
  description?: string
}

export interface ProjectUpdate {
  title?: string
  genre?: Genre
  description?: string
  status?: ProjectStatus
}

// ─── 챕터 ─────────────────────────────────────────────────────────────────────

export interface Chapter {
  id: string
  project_id: string
  chapter_number: number
  title: string | null
  content: string
  word_count: number
  consistency_score: number | null
  created_at: string
  updated_at: string
}

export interface ChapterVersion {
  id: string
  chapter_id: string
  version_number: number
  content: string
  word_count: number
  created_at: string
}

export interface ChapterCreate {
  title?: string
  content?: string
}

export interface ChapterUpdate {
  title?: string
  content?: string
}

export type Tone = 'serious' | 'humorous' | 'dark' | 'lighthearted'

export const TONE_LABELS: Record<Tone, string> = {
  serious: '진지함',
  humorous: '유머러스',
  dark: '어두움',
  lighthearted: '가벼움',
}

export interface GenerationParameters {
  genre: Genre
  tone: Tone
  temperature: number
  max_tokens: number
  user_prompt?: string
}

// ─── 캐릭터 ───────────────────────────────────────────────────────────────────

export interface Character {
  id: string
  project_id: string
  name: string
  age: number | null
  personality_traits: string[]
  appearance: string | null
  background: string | null
  relationships: Record<string, string>
  created_at: string
  updated_at: string
}

export interface CharacterCreate {
  name: string
  age?: number
  personality_traits?: string[]
  appearance?: string
  background?: string
  relationships?: Record<string, string>
}

export interface CharacterUpdate extends Partial<CharacterCreate> {}

// ─── 플롯 ─────────────────────────────────────────────────────────────────────

export type PlotStage =
  | 'exposition'
  | 'rising_action'
  | 'climax'
  | 'falling_action'
  | 'resolution'

export const PLOT_STAGE_LABELS: Record<PlotStage, string> = {
  exposition: '발단',
  rising_action: '전개',
  climax: '절정',
  falling_action: '하강',
  resolution: '결말',
}

export interface PlotPoint {
  id: string
  project_id: string
  title: string
  description: string | null
  plot_stage: PlotStage
  sequence_order: number
  is_completed: boolean
  target_chapter: number | null
  created_at: string
}

export interface PlotPointCreate {
  title: string
  description?: string
  plot_stage: PlotStage
  sequence_order: number
  target_chapter?: number
}

// ─── 세계관 ───────────────────────────────────────────────────────────────────

export type WorldBuildingCategory = 'location' | 'magic_system' | 'technology' | 'culture'

export const WORLDBUILDING_CATEGORY_LABELS: Record<WorldBuildingCategory, string> = {
  location: '장소',
  magic_system: '마법 체계',
  technology: '기술',
  culture: '문화',
}

export interface WorldBuilding {
  id: string
  project_id: string
  category: WorldBuildingCategory
  name: string
  description: string
  rules: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface WorldBuildingCreate {
  category: WorldBuildingCategory
  name: string
  description: string
  rules?: Record<string, unknown>
}

// ─── 일관성 ───────────────────────────────────────────────────────────────────

export type IssueSeverity = 'low' | 'medium' | 'high'
export type IssueType = 'character' | 'plot' | 'worldbuilding'

export interface ConsistencyIssue {
  id: string
  chapter_id: string
  issue_type: IssueType
  severity: IssueSeverity
  description: string
  line_number: number | null
  detected_at: string
  is_resolved: boolean
}

export interface ConsistencyReport {
  chapter_id: string
  score: number
  issues: ConsistencyIssue[]
  checked_at: string
}
