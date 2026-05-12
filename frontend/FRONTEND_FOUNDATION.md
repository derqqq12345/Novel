# Frontend Foundation Implementation

## Overview

This document describes the frontend foundation implementation for the AI Novel Generation Platform (Task 15).

## Implemented Features

### 15.1 라우팅 및 레이아웃 설정 ✅

#### React Router Setup
- **Routes configured:**
  - `/login` - Login page (public)
  - `/register` - Registration page (public)
  - `/dashboard` - Project dashboard (protected)
  - `/editor/:projectId` - Novel editor (protected)
  - `/` - Redirects to dashboard
  - `*` - Catch-all redirects to dashboard

#### Protected Routes
- `ProtectedRoute` component wraps authenticated routes
- Automatically redirects to `/login` if user is not authenticated
- Uses `useAuthStore` to check authentication status

#### Layout Components
- **Header** (`components/layout/Header.tsx`)
  - Logo and app title
  - User info display
  - Logout button
  - Theme toggle (dark/light mode)
  
- **Sidebar** (`components/layout/Sidebar.tsx`)
  - Project navigation
  - Context-aware menu items (shows project-specific items when in editor)
  - Active route highlighting
  
- **Footer** (`components/layout/Footer.tsx`)
  - Copyright information
  
- **MainLayout** (`components/layout/MainLayout.tsx`)
  - Combines Header, Sidebar (optional), and Footer
  - Flexible layout for different page types

### 15.2 API 클라이언트 설정 ✅

#### Axios Instance Configuration
- **Base URL:** Configured via `VITE_API_URL` environment variable (defaults to `/api`)
- **Timeout:** 30 seconds
- **Headers:** JSON content type by default

#### JWT Token Management
- **Request Interceptor:**
  - Automatically attaches JWT token from localStorage to all requests
  - Sets `Authorization: Bearer <token>` header

- **Response Interceptor:**
  - Detects 401 Unauthorized responses
  - Automatically attempts token refresh using refresh token
  - Queues failed requests and retries after successful refresh
  - Prevents multiple simultaneous refresh attempts
  - Clears auth and redirects to login if refresh fails

#### API Modules
- **authApi** (`api/auth.ts`)
  - `login()` - User login
  - `register()` - User registration
  - `refresh()` - Token refresh
  - `logout()` - User logout
  - `me()` - Get current user info

- **projectsApi** (`api/projects.ts`)
  - `list()` - List projects with pagination
  - `get()` - Get project details
  - `create()` - Create new project
  - `update()` - Update project
  - `delete()` - Delete project
  - `export()` - Export project (PDF/EPUB/TXT)

- **chaptersApi** (`api/chapters.ts`)
  - `generate()` - Generate new chapter
  - `list()` - List chapters
  - `get()` - Get chapter details
  - `update()` - Update chapter
  - `delete()` - Delete chapter
  - `regenerate()` - Regenerate chapter with feedback
  - `getVersions()` - Get chapter version history
  - `reorder()` - Reorder chapters
  - `checkConsistency()` - Check chapter consistency

- **charactersApi** (`api/characters.ts`)
  - `list()` - List characters
  - `create()` - Create character
  - `update()` - Update character
  - `delete()` - Delete character

### 15.3 전역 상태 관리 ✅

#### React Query Configuration
- **Stale Time:** 5 minutes (data considered fresh for 5 minutes)
- **Retry:** 2 attempts for queries, 1 for mutations
- **Refetch on Window Focus:** Disabled
- **Configured in:** `main.tsx`

#### Zustand Stores

##### Auth Store (`store/authStore.ts`)
- **State:**
  - `user` - Current user object
- **Actions:**
  - `setUser()` - Set current user
  - `logout()` - Clear auth tokens and user
  - `isAuthenticated()` - Check if user is authenticated

##### Theme Store (`store/themeStore.ts`)
- **State:**
  - `theme` - Current theme ('light' | 'dark' | 'system')
- **Actions:**
  - `setTheme()` - Set theme and apply to DOM
  - `getEffectiveTheme()` - Get actual theme (resolves 'system')
- **Features:**
  - Persists to localStorage
  - Automatically applies theme to `<html>` element
  - Listens to system theme changes
  - Initializes theme on app load

#### Custom Hooks

##### useAuth (`hooks/useAuth.ts`)
- Combines React Query and Zustand for auth operations
- **Returns:**
  - `user` - Current user
  - `isLoading` - Loading state
  - `login()` - Login function
  - `register()` - Register function
  - `logout()` - Logout function
  - Loading states for each operation

##### useProjects (`hooks/useProjects.ts`)
- Manages project CRUD operations with React Query
- **Returns:**
  - `projects` - Project list
  - `total`, `pages` - Pagination info
  - `isLoading`, `error` - Query states
  - `createProject()`, `updateProject()`, `deleteProject()` - Mutation functions
  - Loading states for each mutation

##### useProject (`hooks/useProjects.ts`)
- Fetches single project details
- Automatically refetches when project ID changes

### 15.4 디자인 시스템 구축 ✅

#### TailwindCSS Custom Theme
- **Colors:**
  - Primary: Indigo scale (50-950)
  - Editor backgrounds: Light (#fafaf9) and Dark (#1c1917)
  
- **Fonts:**
  - Sans: Noto Sans KR, Apple SD Gothic Neo, Malgun Gothic
  - Serif: Nanum Myeongjo, Georgia (for novel text)
  - Mono: JetBrains Mono, Fira Code
  
- **Typography:**
  - Line height: 1.8 for Korean text
  - Word break: keep-all (prevents breaking Korean words)
  
- **Animations:**
  - `fade-in` - Fade in effect
  - `slide-up` - Slide up effect

#### Korean Font Integration
- **Google Fonts imported:**
  - Noto Sans KR (300, 400, 500, 700)
  - Nanum Myeongjo (400, 700)
  
- **Novel text styling:**
  - `.novel-text` class for editor content
  - Serif font (Nanum Myeongjo)
  - Line height: 2 for comfortable reading
  - Word break: keep-all

#### Dark/Light Mode Support
- **Implementation:**
  - TailwindCSS `dark:` variant enabled
  - Theme toggle component in header
  - System preference detection
  - Persisted user preference
  
- **Theme modes:**
  - Light - Explicit light theme
  - Dark - Explicit dark theme
  - System - Follows OS preference

#### Common UI Components

##### Button (`components/ui/Button.tsx`)
- **Variants:** primary, secondary, danger, ghost
- **Sizes:** sm, md, lg
- **Features:**
  - Loading state with spinner
  - Disabled state
  - Full TypeScript support
  - Dark mode support

##### Input (`components/ui/Input.tsx`)
- **Features:**
  - Label support
  - Error message display
  - Helper text
  - Dark mode support
  - Forward ref for form libraries

##### Modal (`components/ui/Modal.tsx`)
- **Features:**
  - Backdrop with click-to-close
  - Sizes: sm, md, lg, xl
  - Header with title and close button
  - Body content area
  - Slide-up animation
  - Body scroll lock when open

##### Toast (`components/ui/Toast.tsx`)
- **Types:** success, error, info, warning
- **Features:**
  - Auto-dismiss after 5 seconds
  - Manual dismiss button
  - Stacked notifications
  - Slide-up animation
  - `useToast()` hook for easy usage

##### Spinner (`components/ui/Spinner.tsx`)
- **Sizes:** sm, md, lg
- **Features:**
  - Animated loading indicator
  - Dark mode support

##### Card (`components/ui/Card.tsx`)
- **Components:**
  - `Card` - Main container
  - `CardHeader` - Header section
  - `CardBody` - Content section
  - `CardFooter` - Footer section
- **Features:**
  - Optional hover effect
  - Optional click handler
  - Dark mode support

#### Custom Scrollbar Styling
- Thin scrollbars (8px)
- Rounded thumb
- Dark mode support
- Applied via `.custom-scrollbar` class

## File Structure

```
frontend/src/
├── api/
│   ├── auth.ts           # Auth API client
│   ├── chapters.ts       # Chapters API client
│   ├── characters.ts     # Characters API client
│   ├── client.ts         # Axios instance with interceptors
│   ├── projects.ts       # Projects API client
│   └── index.ts          # API exports
├── components/
│   ├── layout/
│   │   ├── Header.tsx    # App header
│   │   ├── Sidebar.tsx   # Navigation sidebar
│   │   ├── Footer.tsx    # App footer
│   │   └── MainLayout.tsx # Main layout wrapper
│   ├── ui/
│   │   ├── Button.tsx    # Button component
│   │   ├── Input.tsx     # Input component
│   │   ├── Modal.tsx     # Modal component
│   │   ├── Toast.tsx     # Toast notifications
│   │   ├── Spinner.tsx   # Loading spinner
│   │   ├── Card.tsx      # Card component
│   │   └── index.ts      # UI exports
│   ├── ProtectedRoute.tsx # Auth guard
│   └── ThemeToggle.tsx   # Theme switcher
├── hooks/
│   ├── useAuth.ts        # Auth hook
│   └── useProjects.ts    # Projects hook
├── store/
│   ├── authStore.ts      # Auth state (Zustand)
│   └── themeStore.ts     # Theme state (Zustand)
├── types/
│   └── index.ts          # TypeScript types
├── App.tsx               # Main app component
├── main.tsx              # App entry point
├── index.css             # Global styles
└── vite-env.d.ts         # Vite type definitions
```

## Environment Variables

Create a `.env` file in the `frontend/` directory:

```env
VITE_API_URL=http://localhost:8000/api
```

## Usage Examples

### Using the Auth Hook

```typescript
import { useAuth } from './hooks/useAuth'

function LoginPage() {
  const { login, isLoginLoading } = useAuth()
  
  const handleSubmit = async (data) => {
    try {
      await login(data)
      // Redirect handled automatically
    } catch (error) {
      // Handle error
    }
  }
}
```

### Using the Toast System

```typescript
import { useToast } from './components/ui'

function MyComponent() {
  const toast = useToast()
  
  const handleSuccess = () => {
    toast.success('작업이 완료되었습니다!')
  }
  
  const handleError = () => {
    toast.error('오류가 발생했습니다.')
  }
}
```

### Using the Theme Toggle

```typescript
import { useThemeStore } from './store/themeStore'

function MyComponent() {
  const { theme, setTheme } = useThemeStore()
  
  return (
    <button onClick={() => setTheme('dark')}>
      다크 모드
    </button>
  )
}
```

## Testing

Run type checking:
```bash
npm run type-check
```

Run development server:
```bash
npm run dev
```

Build for production:
```bash
npm run build
```

## Next Steps

The frontend foundation is now complete. The following features can now be built on top of this foundation:

1. **Authentication Pages** (Task 16)
   - Login page with form validation
   - Registration page
   
2. **Project Dashboard** (Task 17)
   - Project list with cards
   - Create project modal
   - Delete confirmation
   
3. **Novel Editor** (Task 18)
   - Rich text editor
   - Chapter list
   - Generation controls
   - Context sidebar
   
4. **Character Management** (Task 19)
5. **Plot Management** (Task 20)
6. **World Building** (Task 21)
7. **Export UI** (Task 22)

All of these features can leverage the routing, API clients, state management, and UI components implemented in this task.
