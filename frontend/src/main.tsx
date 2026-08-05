import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import ConversationPage from './pages/ConversationPage.tsx'
import App from './App.tsx'

import './index.css'

const queryClient = new QueryClient()

createRoot(document.getElementById('root') as HTMLElement).render(
    <StrictMode>
        <QueryClientProvider client={queryClient}>
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<App />} />
                    <Route path="/conversation/:conversationId" element={<ConversationPage />} />
                </Routes>
            </BrowserRouter>
        </QueryClientProvider>
    </StrictMode>,
)
