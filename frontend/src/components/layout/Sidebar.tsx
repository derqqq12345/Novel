import { Link, useLocation } from 'react-router-dom'
import { ReactNode } from 'react'

interface SidebarProps {
  projectId?: string
}

interface NavItemProps {
  to: string
  icon: ReactNode
  label: string
  isActive: boolean
}

function NavItem({ to, icon, label, isActive }: NavItemProps) {
  return (
    <Link
      to={to}
      className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
        isActive
          ? 'bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300'
          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
      }`}
    >
      <span className="text-xl">{icon}</span>
      <span className="font-medium">{label}</span>
    </Link>
  )
}

export default function Sidebar({ projectId }: SidebarProps) {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <aside className="w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 h-full overflow-y-auto">
      <nav className="p-4 space-y-2">
        <NavItem
          to="/dashboard"
          icon="📚"
          label="프로젝트 목록"
          isActive={isActive('/dashboard')}
        />

        {projectId && (
          <>
            <div className="pt-4 pb-2 px-4">
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                프로젝트
              </h3>
            </div>
            <NavItem
              to={`/editor/${projectId}`}
              icon="✍️"
              label="에디터"
              isActive={isActive(`/editor/${projectId}`)}
            />
            <NavItem
              to={`/editor/${projectId}/characters`}
              icon="👥"
              label="캐릭터"
              isActive={isActive(`/editor/${projectId}/characters`)}
            />
            <NavItem
              to={`/editor/${projectId}/plot`}
              icon="📊"
              label="플롯"
              isActive={isActive(`/editor/${projectId}/plot`)}
            />
            <NavItem
              to={`/editor/${projectId}/worldbuilding`}
              icon="🌍"
              label="세계관"
              isActive={isActive(`/editor/${projectId}/worldbuilding`)}
            />
          </>
        )}
      </nav>
    </aside>
  )
}
