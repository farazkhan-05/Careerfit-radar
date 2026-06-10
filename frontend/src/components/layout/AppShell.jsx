import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function AppShell() {
  return (
    <div className="app-canvas min-h-screen">
      <Sidebar />
      <main className="min-h-screen pt-28 lg:pl-72 lg:pt-0">
        <Outlet />
      </main>
    </div>
  )
}
