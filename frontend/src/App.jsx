import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AppShell from './components/layout/AppShell'
import { PageSpinner } from './components/ui/Spinner'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Resume = lazy(() => import('./pages/Resume'))
const FindJobs = lazy(() => import('./pages/FindJobs'))
const Jobs = lazy(() => import('./pages/Jobs'))
const Applications = lazy(() => import('./pages/Applications'))
const Settings = lazy(() => import('./pages/Settings'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60_000,
      gcTime: 30 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
      refetchOnMount: false,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<PageSpinner />}>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<Dashboard />} />
              <Route path="resume" element={<Resume />} />
              <Route path="find-jobs" element={<FindJobs />} />
              <Route path="jobs" element={<Jobs />} />
              <Route path="applications" element={<Applications />} />
              <Route path="settings" element={<Settings />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
