import { useEffect, useRef, useState } from 'react'
import { api, openPdf } from '../api'
import { useAuth } from '../AuthContext'
import { Alert, Field, Page, fmtDate, useConfirm, useToast } from '../ui'

// Fields each role may edit (must match EDITABLE_FIELDS in the Django models).
const FIELDS = {
  student: [['name', 'Full name'], ['branch', 'Branch'], ['cgpa', 'CGPA'], ['phone', 'Phone'], ['address', 'Address']],
  officer: [['name', 'Full name'], ['department', 'Department'], ['phone', 'Phone']],
  admin: [['name', 'Full name']],
}

export default function Profile() {
  const { user, setUser } = useAuth()
  const [form, setForm] = useState(user)
  const [error, setError] = useState('')
  const toast = useToast()
  useEffect(() => { setForm(user) }, [user])

  async function save(e) {
    e.preventDefault()
    const body = Object.fromEntries(FIELDS[user.role].map(([k]) => [k, form[k]]))
    try { setUser(await api('/auth/profile/', { method: 'PUT', body })); setError(''); toast('Profile saved') }
    catch (err) { setError(err.message) }
  }

  // Profile completeness meter (students): every filled field + resume counts.
  const parts = user.role === 'student' ? [...FIELDS.student.map(([k]) => !!form[k]), user.has_resume] : []
  const pct = parts.length ? Math.round((parts.filter(Boolean).length / parts.length) * 100) : null

  return (
    <Page title="My profile">
      {pct !== null && (
        <div className="card meter"><div className="row between"><strong>Profile completeness</strong><b>{pct}%</b></div>
          <div className="bar-track"><div className="bar-fill" style={{ width: `${pct}%` }} /></div>
          {pct < 100 && <small className="muted">{user.has_resume ? 'Fill in the remaining fields to reach 100%.' : 'Upload your resume to apply for jobs.'}</small>}
        </div>
      )}
      {user.role === 'student' && <ResumeCard user={user} setUser={setUser} />}
      <form className="card form" onSubmit={save}>
        <Alert>{error}</Alert>
        <div className="grid2">
          <Field label="Email"><input value={user.email} disabled /></Field>
          {user.roll_no && <Field label="Roll number"><input value={user.roll_no} disabled /></Field>}
          {FIELDS[user.role].map(([k, label]) => (
            <Field key={k} label={label}><input value={form[k] ?? ''} type={k === 'cgpa' ? 'number' : 'text'} step="0.01" onChange={(e) => setForm({ ...form, [k]: e.target.value })} /></Field>
          ))}
        </div>
        <button className="btn">Save changes</button>
      </form>
    </Page>
  )
}

// Drag and drop (or click) a PDF resume.
function ResumeCard({ user, setUser }) {
  const [over, setOver] = useState(false)
  const [busy, setBusy] = useState(false)
  const input = useRef(null)
  const toast = useToast()
  const confirm = useConfirm()

  async function upload(file) {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) return toast('Resume must be a PDF file.', 'error')
    if (file.size > 2 * 1024 * 1024) return toast('Resume must be smaller than 2 MB.', 'error')
    const body = new FormData(); body.append('resume', file)
    setBusy(true)
    try { setUser(await api('/auth/resume/', { method: 'POST', body })); toast('Resume uploaded') }
    catch (err) { toast(err.message, 'error') }
    finally { setBusy(false) }
  }
  async function remove() {
    if (!(await confirm('Remove your resume? You will not be able to apply until you upload another.'))) return
    setUser(await api('/auth/resume/', { method: 'DELETE' })); toast('Resume removed')
  }

  return (
    <div className="card">
      <h3>Resume</h3>
      <div className={`drop ${over ? 'over' : ''}`} onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); upload(e.dataTransfer.files[0]) }} onClick={() => input.current.click()}
        role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && input.current.click()}>
        <input ref={input} type="file" accept="application/pdf,.pdf" hidden onChange={(e) => { upload(e.target.files[0]); e.target.value = '' }} />
        {busy ? 'Uploading…' : user.has_resume ? 'Drop a new PDF here to replace your resume' : 'Drop your resume here, or click to choose a PDF (max 2 MB)'}
      </div>
      {user.has_resume && (
        <div className="row" style={{ marginTop: '.75rem' }}>
          <button className="btn ghost" onClick={() => openPdf(`/students/${user.id}/resume/`).catch((e) => toast(e.message, 'error'))}>View resume</button>
          <button className="link danger" onClick={remove}>Remove</button>
          <span className="muted">Uploaded {fmtDate(user.resume_updated)}</span>
        </div>
      )}
    </div>
  )
}
