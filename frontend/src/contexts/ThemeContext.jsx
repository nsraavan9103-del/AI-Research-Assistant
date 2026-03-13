import React, { createContext, useContext, useEffect, useState } from 'react'

const ThemeContext = createContext({
  theme: 'system',
  setTheme: () => {},
  resolvedTheme: 'light',
})

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(
    () => localStorage.getItem('theme') ?? 'system'
  )

  const getResolved = (t) =>
    t === 'system'
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      : t

  const [resolvedTheme, setResolvedTheme] = useState(() => getResolved(theme))

  useEffect(() => {
    const resolved = getResolved(theme)
    setResolvedTheme(resolved)
    document.documentElement.setAttribute('data-theme', resolved)
    localStorage.setItem('theme', theme)
  }, [theme])

  useEffect(() => {
    if (theme !== 'system') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => {
      const r = mq.matches ? 'dark' : 'light'
      setResolvedTheme(r)
      document.documentElement.setAttribute('data-theme', r)
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [theme])

  const setTheme = (t) => setThemeState(t)

  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolvedTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = () => useContext(ThemeContext)
