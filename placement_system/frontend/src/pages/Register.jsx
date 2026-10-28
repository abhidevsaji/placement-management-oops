
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Field } from '../ui'

const EMPTY = {
  name: '',
  email: '',
  password: '',
  roll_no: '',
  branch: '',
  cgpa: '',
  phone: '',
  address: '',
  department: '',
}

export default function Register() {
  const [role, setRole] = useState('student')
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [done, setDone] = useState('')

  const set = (key) => (e) =>
    setForm((previous) => ({ ...previous, [key]: e.target.value }))

  async function submit(e) {
    e.preventDefault()
    setError('')
    setDone('')

    const body =
      role === 'student'
        ? {
            name: form.name,
            email: form.email,
            password: form.password,
            roll_no: form.roll_no,
            branch: form.branch,
            cgpa: form.cgpa,
            phone: form.phone,
            address: form.address,
          }
        : {
            name: form.name,
            email: form.email,
            password: form.password,
            department: form.department,
            phone: form.phone,
          }

    try {
      const data = await api(`/auth/register/${role}/`, {
        method: 'POST',
        body,
      })
      setDone(data.detail || 'Your registration has been submitted for approval.')
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.')
    }
  }

  if (done) {
    return (
      <main className="auth-shell">
        <section className="auth-panel auth-panel-centered">
          <div className="auth-brand">
            <div className="auth-logo">C</div>
            <span>CUCEK <strong>Placement</strong></span>
          </div>

          <div className="auth-card register-card">
            <div className="success-icon">✓</div>
            <p className="auth-eyebrow">REGISTRATION COMPLETE</p>
            <h1>You're on your way!</h1>
            <p className="auth-description">{done}</p>
            <Link className="auth-submit" to="/login">
              Back to login <span>→</span>
            </Link>
          </div>

          <p className="auth-copyright">
            © CUCEK Placement · All rights reserved
          </p>
        </section>
      </main>
    )
  }

  return (
    <main className="auth-shell">
      <section className="auth-panel auth-panel-centered">
        <div className="auth-brand">
          <div className="auth-logo">C</div>
          <span>CUCEK <strong>Placement</strong></span>
        </div>

        <div className="auth-card register-card">
          <p className="auth-eyebrow">JOIN OUR COMMUNITY</p>
          <h1>Create your account</h1>
          <p className="auth-description">
            Get started with your campus placement journey.
          </p>

          <div className="register-role-label">I want to register as</div>
          <div className="register-roles" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={role === 'student'}
              className={role === 'student' ? 'active' : ''}
              onClick={() => {
                setRole('student')
                setError('')
              }}
            >
              <span className="role-icon">♙</span>
              <span>
                <strong>Student</strong>
                <small>Find opportunities</small>
              </span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={role === 'officer'}
              className={role === 'officer' ? 'active' : ''}
              onClick={() => {
                setRole('officer')
                setError('')
              }}
            >
              <span className="role-icon">▤</span>
              <span>
                <strong>Placement Officer</strong>
                <small>Manage placements</small>
              </span>
            </button>
          </div>

          <form onSubmit={submit}>
            <Alert>{error}</Alert>

            <div className="register-fields">
              <Field label="Full name">
                <input
                  required
                  autoComplete="name"
                  placeholder="Enter your full name"
                  value={form.name}
                  onChange={set('name')}
                />
              </Field>

              <Field label="Email address">
                <input
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={set('email')}
                />
              </Field>

              <Field label="Phone number">
                <input
                  type="tel"
                  required
                  pattern="[0-9]{10}"
                  maxLength={10}
                  autoComplete="tel"
                  placeholder="10-digit mobile number"
                  value={form.phone}
                  onChange={set('phone')}
                />
              </Field>

              <Field label="Password" hint="Use at least 8 characters.">
                <input
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  placeholder="Create a strong password"
                  value={form.password}
                  onChange={set('password')}
                />
              </Field>

              {role === 'student' ? (
                <>
                  <div className="register-fields-row">
                    <Field label="Roll number">
                      <input
                        required
                        placeholder="Your roll number"
                        value={form.roll_no}
                        onChange={set('roll_no')}
                      />
                    </Field>

                    <Field label="Branch">
                      <input
                        required
                        placeholder="e.g. IT"
                        value={form.branch}
                        onChange={set('branch')}
                      />
                    </Field>
                  </div>

                  <div className="register-fields-row">
                    <Field label="CGPA" hint="Between 0 and 10">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        max="10"
                        required
                        placeholder="e.g. 7.50"
                        value={form.cgpa}
                        onChange={set('cgpa')}
                      />
                    </Field>

                    <Field label="Address">
                      <input
                        placeholder="Your address"
                        value={form.address}
                        onChange={set('address')}
                      />
                    </Field>
                  </div>
                </>
              ) : (
                <Field label="Department">
                  <input
                    required
                    placeholder="Enter your department"
                    value={form.department}
                    onChange={set('department')}
                  />
                </Field>
              )}
            </div>

            <button className="auth-submit" type="submit">
              Submit for approval <span>→</span>
            </button>
          </form>

          <p className="auth-switch">
            Already have an account? <Link to="/login">Log in</Link>
          </p>
        </div>

        <p className="auth-copyright">
          © CUCEK Placement · All rights reserved
        </p>
      </section>
    </main>
  )
}

