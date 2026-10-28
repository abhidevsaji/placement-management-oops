import { useState } from 'react'
import { api, openPdf } from '../../api'
import { Alert, Async, Badge, Empty, Modal, Page, fmtDate, useApi, useToast } from '../../ui'

// Same rules as Application.TRANSITIONS in Django.
const NEXT = { applied: [['shortlisted', 'Shortlist'], ['rejected', 'Reject']], shortlisted: [['placed', 'Mark placed'], ['rejected', 'Reject']] }

export default function Applications() {
  const [filters, setFilters] = useState({ job: '', status: '', q: '' })
  const query = new URLSearchParams(Object.entries(filters).filter(([, v]) => v)).toString()
  const state = useApi(`/applications/${query ? `?${query}` : ''}`)
  const jobs = useApi('/jobs/')
  const [error, setError] = useState('')
  const [view, setView] = useState(null)
  const toast = useToast()

  async function change(a, status) {
    try { await api(`/applications/${a.id}/status/`, { method: 'PATCH', body: { status } }); setError(''); toast(`${a.student_name}: ${status}`); state.reload() }
    catch (err) { setError(err.message) }
  }
  const set = (k) => (e) => setFilters({ ...filters, [k]: e.target.value })

  return (
    <Page title="Student applications">
      <div className="filters">
        <input placeholder="Search name or roll number" value={filters.q} onChange={set('q')} />
        <select value={filters.job} onChange={set('job')}><option value="">All jobs</option>{(jobs.data || []).map((j) => <option key={j.id} value={j.id}>{j.title} – {j.company_name}</option>)}</select>
        <select value={filters.status} onChange={set('status')}><option value="">All statuses</option>{['applied', 'shortlisted', 'rejected', 'placed'].map((s) => <option key={s} value={s}>{s}</option>)}</select>
      </div>
      <Alert>{error}</Alert>
      <Async state={state}>{(list) => list.length === 0 ? <Empty>No applications match these filters.</Empty> : (
        <div className="table-wrap"><table>
          <thead><tr><th>Student</th><th>Roll no.</th><th>Branch</th><th>CGPA</th><th>Job</th><th>Applied</th><th>Status</th><th>Update</th></tr></thead>
          <tbody>{list.map((a) => (
            <tr key={a.id}><td><button className="link" onClick={() => setView(a)}>{a.student_name}</button></td><td>{a.roll_no}</td><td>{a.branch}</td><td>{a.cgpa}</td><td>{a.job_title}<br /><small>{a.company_name}</small></td><td>{fmtDate(a.applied_date)}</td><td><Badge value={a.status} /></td>
              <td className="actions">{(NEXT[a.status] || []).map(([s, label]) => <button key={s} className={s === 'rejected' ? 'link danger' : 'link'} onClick={() => change(a, s)}>{label}</button>)}{!NEXT[a.status] && <span className="muted">Final</span>}</td></tr>
          ))}</tbody>
        </table></div>
      )}</Async>
      {view && (
        <Modal title={view.student_name} onClose={() => setView(null)}>
          <dl>
            <div><dt>Roll number</dt><dd>{view.roll_no}</dd></div><div><dt>Branch</dt><dd>{view.branch}</dd></div>
            <div><dt>CGPA</dt><dd>{view.cgpa}</dd></div><div><dt>Phone</dt><dd>{view.phone}</dd></div>
            <div><dt>Email</dt><dd>{view.email}</dd></div><div><dt>Applied for</dt><dd>{view.job_title}</dd></div>
          </dl>
          {view.has_resume ? <button className="btn" onClick={() => openPdf(`/students/${view.student}/resume/`).catch((e) => toast(e.message, 'error'))}>Open resume (PDF)</button> : <span className="muted">No resume on file.</span>}
        </Modal>
      )}
    </Page>
  )
}
