import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'

/**
 * TanStack Query client — configured at the app root.
 * defaultOptions can be tuned per-module as needed.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Don't retry on 401/403 — those are auth failures, not transient errors.
      retry: (failureCount, error: unknown) => {
        const status = (error as { response?: { status?: number } })?.response?.status
        if (status === 401 || status === 403) return false
        return failureCount < 2
      },
      staleTime: 1000 * 30, // 30 seconds
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
