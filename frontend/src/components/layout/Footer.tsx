export default function Footer() {
  return (
    <footer className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 py-4">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center text-sm text-gray-600 dark:text-gray-400">
          © {new Date().getFullYear()} AI 장편소설 생성 플랫폼. All rights reserved.
        </div>
      </div>
    </footer>
  )
}
