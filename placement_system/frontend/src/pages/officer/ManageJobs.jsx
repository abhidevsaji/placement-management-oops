import { useState } from 'react'
import { api } from '../../api'
import { Alert, Async, Badge, Empty, Field, Page, fmtDate, useApi, useConfirm, useToast } from '../../ui'

const BLANK = { company: '', title: '', description: '', package: '', eligibility_criteria: '', min_cgpa: 0, allowed_branches: '', last_date: '', status: 'open' }

export default function ManageJobs() {
  const jobs = useApi('/jobs/')
  const confirm = useConfirm()
  const toast = useToast()
  const companies = useApi('/companies/')
  const [form, setForm] = useState(null)
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function save(e) {
    e.preventDefault(); setError('')
    try {
      await api(form.id ? `/jobs/${form.id}/` : '/jobs/', { method: form.id ? 'PUT' : 'POST', body: form })
      setForm(null); jobs.reload()
    } catch (err) { setError(err.message) }
  }
  async function remove(j) {
    if (!(await confirm(`Delete "${j.title}"? Applications for it will be deleted too.`))) return
    await api(`/jobs/${j.id}/`, { method: 'DELETE' }); jobs.reload()
  }
  async function toggle(j) {
    await api(`/jobs/${j.id}/`, { method: 'PATCH', body: { status: j.status === 'open' ? 'closed' : 'open' } }); jobs.reload()
  }
  const activeCompanies = (companies.data || []).filter((c) => c.status === 'active')

  return (
    <Page title="Job postings" action={!form && <button className="btn" onClick={() => setForm({ ...BLANK, company: activeCompanies[0]?.id ?? '' })}>Post a job</button>}>
      {form && (
        <form className="card form" onSubmit={save}>
          <h3>{form.id ? 'Edit job' : 'Post a job'}</h3>
          <Alert>{error}</Alert>
          <div className="grid2">
            <Field label="Company"><select required value={form.company} onChange={set('company')}>
              <option value="" disabled>Select company</option>
              {(form.id ? companies.data || [] : activeCompanies).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select></Field>
            <Field label="Job title"><input required value={form.title} onChange={set('title')} /></Field>
            <Field label="Package" hint="For example 6 LPA"><input required value={form.package} onChange={set('package')} /></Field>
            <Field label="Last date to apply"><input type="date" required value={form.last_date} onChange={set('last_date')} /></Field>
            <Field label="Minimum CGPA"><input type="number" step="0.1" min="0" max="10" value={form.min_cgpa} onChange={set('min_cgpa')} /></Field>
            <Field label="Allowed branches" hint="Comma separated, e.g. CSE, IT. Leave empty for all."><input value={form.allowed_branches} onChange={set('allowed_branches')} /></Field>
          </div>
          <Field label="Description"><textarea rows="3" required value={form.description} onChange={set('description')} /></Field>
          <Field label="Eligibility notes" hint="Shown to students"><textarea rows="2" value={form.eligibility_criteria} onChange={set('eligibility_criteria')} /></Field>
          {!form.id && <p className="muted">Eligible students are notified automatically when you post.</p>}
          <div className="row"><button className="btn">{form.id ? 'Save job' : 'Post job'}</button><button type="button" className="btn ghost" onClick={() => setForm(null)}>Cancel</button></div>
        </form>
      )}
      <Async state={jobs}>{(list) => list.length === 0 ? <Empty>No jobs posted yet.</Empty> : (
        <div className="table-wrap"><table>
          <thead><tr><th>Job</th><th>Company</th><th>Package</th><th>Min CGPA</th><th>Last date</th><th>Applicants</th><th>Status</th><th></th></tr></thead>
          <tbody>{list.map((j) => (
            <tr key={j.id}><td>{j.title}</td><td>{j.company_name}</td><td>{j.package}</td><td>{j.min_cgpa}</td><td>{fmtDate(j.last_date)}</td><td>{j.applications_count}</td><td><Badge value={j.status} /></td>
              <td className="actions"><button className="link" onClick={() => setForm(j)}>Edit</button><button className="link" onClick={() => toggle(j)}>{j.status === 'open' ? 'Close' : 'Reopen'}</button><button className="link danger" onClick={() => remove(j)}>Delete</button></td></tr>
          ))}</tbody>
        </table></div>
      )}</Async>
    </Page>
  )
}
