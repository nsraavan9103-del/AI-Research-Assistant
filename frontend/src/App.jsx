import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import { useStore } from './store/useStore'
import AuthPage from './pages/AuthPage'
import ChatPage from './pages/ChatPage'

function PrivateRoute({ children }) {
  const { accessToken } = useStore()
  return accessToken ? <>{children}</> : <Navigate to="/auth" replace />
}

export default function App() {
  return (
    <ThemeProvider>
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
        <Route
          path="/chat"
          element={
            <PrivateRoute>
              <ChatPage />
            </PrivateRoute>
          }
        />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </ThemeProvider>
  )
}
