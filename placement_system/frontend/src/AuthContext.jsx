import { createContext, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from './api'

const AuthContext = createContext(null)
export const useAuth = () => useContext(AuthContext)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!getToken())

  // Restore the session if a token is already saved in the browser.
  useEffect(() => {
    if (!getToken()) return
    api('/auth/profile/')
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [])

  async function login(email, password) {
    const data = await api('/auth/login/', { method: 'POST', body: { email, password } })
    setToken(data.token)
    setUser(data.user)
    return data.user
  }

  async function logout() {
    try { await api('/auth/logout/', { method: 'POST' }) } catch { /* token may already be invalid */ }
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, setUser, login, logout, loading }}>{children}</AuthContext.Provider>
  )
}
