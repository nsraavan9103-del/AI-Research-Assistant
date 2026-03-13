import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useStore } from '../store/useStore'
import { useTheme } from '../contexts/ThemeContext'

export default function AuthPage() {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  const { setTokens, setUser } = useStore()
  const navigate = useNavigate()
  const { resolvedTheme, setTheme, theme } = useTheme()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      if (mode === 'register') {
        await axios.post('/api/auth/register', {
          email,
          password,
          full_name: fullName || undefined,
        })
        setSuccess('Account created! Please log in.')
        setMode('login')
      } else {
        const params = new URLSearchParams()
        params.append('username', email)
        params.append('password', password)

        const { data } = await axios.post('/api/auth/login', params, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        })
        setTokens(data.access_token, data.refresh_token)
        setUser({ id: '', email, full_name: '', role: 'user' })
        navigate('/chat')
      }
    } catch (err) {
      setError(
        axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? err.message)
          : 'Something went wrong'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      <button
        className="fixed top-4 right-4 p-2 rounded-full transition-all hover:scale-110"
        style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
        onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
        title="Toggle dark mode"
      >
        {resolvedTheme === 'dark' ? '☀️' : '🌙'}
      </button>

      <div
        className="w-full max-w-md mx-4 rounded-2xl p-8 shadow-card-lg"
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border)',
        }}
      >
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">🔬</div>
          <h1 className="text-2xl font-bold text-base-content">AI Research Assistant</h1>
          <p className="text-sm mt-1 text-muted">
            {mode === 'login' ? 'Sign in to your account' : 'Create a new account'}
          </p>
        </div>

        <div
          className="flex rounded-xl mb-6 p-1"
          style={{ backgroundColor: 'var(--bg-secondary)' }}
        >
          {['login', 'register'].map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(null); setSuccess(null) }}
              className="flex-1 py-2 rounded-lg text-sm font-medium transition-all"
              style={
                mode === m
                  ? {
                      backgroundColor: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      boxShadow: 'var(--shadow)',
                    }
                  : { color: 'var(--text-secondary)' }
              }
            >
              {m === 'login' ? 'Sign In' : 'Sign Up'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'register' && (
            <div>
              <label className="block text-sm font-medium mb-1 text-base-content">
                Full Name (optional)
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-xl px-4 py-2.5 text-sm border transition-all"
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  borderColor: 'var(--border)',
                  color: 'var(--text-primary)',
                }}
                placeholder="Dr. Jane Smith"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1 text-base-content">
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl px-4 py-2.5 text-sm border transition-all"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                borderColor: 'var(--border)',
                color: 'var(--text-primary)',
              }}
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1 text-base-content">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl px-4 py-2.5 text-sm border transition-all"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                borderColor: 'var(--border)',
                color: 'var(--text-primary)',
              }}
              placeholder={mode === 'register' ? 'Min. 8 chars with letters + digits' : '••••••••'}
            />
          </div>

          {error && (
            <div
              className="rounded-xl px-4 py-3 text-sm animate-fade-in"
              style={{ backgroundColor: 'color-mix(in srgb, #ef4444 12%, transparent)', color: '#ef4444' }}
            >
              {error}
            </div>
          )}
          {success && (
            <div
              className="rounded-xl px-4 py-3 text-sm animate-fade-in"
              style={{ backgroundColor: 'color-mix(in srgb, #22c55e 12%, transparent)', color: '#22c55e' }}
            >
              {success}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl font-semibold text-sm transition-all hover:opacity-90 disabled:opacity-60"
            style={{
              background: 'linear-gradient(135deg, var(--accent), var(--accent-light))',
              color: '#ffffff',
            }}
          >
            {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  )
}
