import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ToastProvider } from '@/components/molecules/Toast'
import { I18nWrapper } from '@/components/templates/I18nWrapper'
import { App } from '@/App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <I18nWrapper>
          <ToastProvider>
            <App />
          </ToastProvider>
        </I18nWrapper>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
