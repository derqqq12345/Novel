import { ReactNode } from 'react'
import Header from './Header'
import Footer from './Footer'
import Sidebar from './Sidebar'

interface MainLayoutProps {
  children: ReactNode
  showSidebar?: boolean
  projectId?: string
}

export default function MainLayout({ children, showSidebar = false, projectId }: MainLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-950">
      <Header />
      
      <div className="flex-1 flex">
        {showSidebar && <Sidebar projectId={projectId} />}
        
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
      
      <Footer />
    </div>
  )
}
