
import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { Alert } from '../ui'

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  if (user) return <Navigate to="/" replace />

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(form.email, form.password)
      navigate('/')
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        'Unable to sign in. Please check your credentials.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="placehub-login">
      <section className="placehub-welcome">
        <Link to="/" className="placehub-brand">
          <span className="placehub-logo">C</span>
          <span>CUCEK <strong>Placement</strong></span>
        </Link>

        <div className="welcome-content">
          <span className="welcome-tag">YOUR CAREER STARTS HERE</span>
          <h1>Turn your<br />ambitions into<br /><span>achievements.</span></h1>
          <p>
            Your journey from campus to career begins here.
            Discover opportunities, connect with companies, and take
            the next step towards your future.
          </p>

          <div className="welcome-illustration" aria-hidden="true">
            <div className="illustration-circle">
              <div className="illustration-card">
                <div className="illustration-avatar">C</div>
                <div className="illustration-line long" />
                <div className="illustration-line short" />
                <div className="illustration-check">✓</div>
              </div>
              <div className="illustration-star">✦</div>
              <div className="illustration-dot dot-one" />
              <div className="illustration-dot dot-two" />
            </div>
          </div>

          <div className="welcome-points">
            <span>✓ Verified opportunities</span>
            <span>✓ One platform, endless possibilities</span>
          </div>
        </div>

        <footer className="welcome-footer">
          CUCEK · Campus Placement Portal
        </footer>
      </section>

      <section className="placehub-form-side">
        <div className="placehub-form">
          <div className="form-heading">
            <span className="form-eyebrow">WELCOME BACK</span>
            <h2>Sign in to CUCEK Placement</h2>
            <p>Enter your account details to continue.</p>
          </div>

          {error && <Alert>{error}</Alert>}

          <form onSubmit={handleSubmit}>
            <label className="placehub-label" htmlFor="email">
              Email address
            </label>
            <input
              id="email"
              className="placehub-input"
              type="email"
              name="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={handleChange}
              autoComplete="username"
              required
            />

            <div className="password-heading">
              <label className="placehub-label" htmlFor="password">
                Password
              </label>
            </div>

            <div className="password-field">
              <input
                id="password"
                className="placehub-input"
                type={showPassword ? 'text' : 'password'}
                name="password"
                placeholder="Enter your password"
                value={form.password}
                onChange={handleChange}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>

            <button
              className="placehub-submit"
              type="submit"
              disabled={loading}
            >
              {loading ? 'Signing in...' : 'Sign in'}
              {!loading && <span aria-hidden="true">→</span>}
            </button>
          </form>

          <p className="placehub-register">
            Don't have an account? <Link to="/register">Create account</Link>
          </p>

          <div className="placehub-security">
            <span aria-hidden="true">🔒</span>
            Your information is protected by secure sign-in.
          </div>

          <footer className="copyright">
            © CUCEK Placement · All rights reserved
          </footer>
        </div>
      </section>
    </main>
  )
}
