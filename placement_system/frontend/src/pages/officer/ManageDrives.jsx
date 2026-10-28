import { useState } from 'react'
import { api } from '../../api'
import { Alert, Async, Badge, Empty, Field, Page, fmtDate, useApi } from '../../ui'

export default function ManageDrives() {
  const drives = useApi('/drives/')
  const jobs = useApi('/jobs/?status=open')
  const [form, setForm] = useState(null)
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function save(e) {
    e.preventDefault(); setError('')
    try { await api('/drives/', { method: 'POST', body: form }); setForm(null); drives.reload() }
    catch (err) { setError(err.message) }
  }
  async function setStatus(d, status) { await api(`/drives/${d.id}/`, { method: 'PATCH', body: { status } }); drives.reload() }

  return (
    <Page title="Placement drives" action={!form && <button className="btn" onClick={() => setForm({ job: jobs.data?.[0]?.id ?? '', drive_date: '', venue: '', description: '' })}>Schedule a drive</button>}>
      {form && (
        <form className="card form" onSubmit={save}>
          <h3>Schedule a drive</h3>
          <Alert>{error}</Alert>
          <div className="grid2">
            <Field label="Job"><select required value={form.job} onChange={set('job')}><option value="" disabled>Select job</option>{(jobs.data || []).map((j) => <option key={j.id} value={j.id}>{j.title} – {j.company_name}</option>)}</select></Field>
            <Field label="Date"><input type="date" required value={form.drive_date} onChange={set('drive_date')} /></Field>
            <Field label="Venue"><input required value={form.venue} onChange={set('venue')} /></Field>
          </div>
          <Field label="Details"><textarea rows="2" value={form.description} onChange={set('description')} /></Field>
          <p className="muted">Applicants who are not rejected are notified automatically.</p>
          <div className="row"><button className="btn">Schedule and notify</button><button type="button" className="btn ghost" onClick={() => setForm(null)}>Cancel</button></div>
        </form>
      )}
      <Async state={drives}>{(list) => list.length === 0 ? <Empty>No drives scheduled yet.</Empty> : (
        <div className="table-wrap"><table>
          <thead><tr><th>Date</th><th>Company</th><th>Job</th><th>Venue</th><th>Status</th><th></th></tr></thead>
          <tbody>{list.map((d) => (
            <tr key={d.id}><td>{fmtDate(d.drive_date)}</td><td>{d.company_name}</td><td>{d.job_title}</td><td>{d.venue}</td><td><Badge value={d.status} /></td>
              <td className="actions">{d.status === 'scheduled' && <><button className="link" onClick={() => setStatus(d, 'completed')}>Mark completed</button><button className="link danger" onClick={() => setStatus(d, 'cancelled')}>Cancel</button></>}</td></tr>
          ))}</tbody>
        </table></div>
      )}</Async>
    </Page>
  )
}
