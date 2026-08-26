import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AuthProvider } from '@/contexts/auth/AuthProvider.tsx'

import ConversationPage from './pages/ConversationPage.tsx'
import ConversationsPage from './pages/ConversationsPage.tsx'
import LoginPage from './pages/LoginPage.tsx'
import App from './App.tsx'

import './index.css'

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnMount: false,
            refetchOnWindowFocus: false,
        },
    },
})

createRoot(document.getElementById('root') as HTMLElement).render(
    <StrictMode>
        <QueryClientProvider client={queryClient}>
            <AuthProvider>
                <BrowserRouter>
                    <Routes>
                        <Route path="/login" element={<LoginPage />} />
                        <Route element={<ProtectedRoute />}>
                            <Route path="/" element={<App />} />
                            <Route path="/conversations" element={<ConversationsPage />} />
                            <Route path="/conversations/:conversationId" element={<ConversationPage />} />
                        </Route>
                    </Routes>
                </BrowserRouter>
            </AuthProvider>
        </QueryClientProvider>
    </StrictMode>,
)
