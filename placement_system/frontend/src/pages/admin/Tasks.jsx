import { useState } from 'react'
import { api } from '../../api'
import { Alert, Async, Badge, Empty, Field, Page, fmtDate, useApi, useConfirm, useToast } from '../../ui'

// The task list mirrors the Placement Officer operations in the class diagram.
const TYPES = [
  ['add_company', 'Add / update company details'], ['post_job', 'Post a job opening'], ['set_eligibility', 'Set eligibility criteria'],
  ['review_applications', 'Review student applications'], ['shortlist', 'Shortlist students'], ['schedule_drive', 'Schedule a placement drive'],
  ['notify_students', 'Notify eligible students'], ['publish_results', 'Publish placement results'], ['other', 'Other (write your own)'],
]
const BLANK = { task_type: 'shortlist', title: TYPES[4][1], description: '', assigned_to: '', company: '', priority: 'medium', due_date: '' }

export default function Tasks() {
  const [filter, setFilter] = useState('')
  const tasks = useApi(`/tasks/${filter ? `?status=${filter}` : ''}`)
  const officers = useApi('/admin/users/?role=officer&status=approved')
  const companies = useApi('/companies/')
  const [form, setForm] = useState(null)
  const [error, setError] = useState('')
  const toast = useToast()
  const confirm = useConfirm()
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  function pickType(e) {
    const type = e.target.value
    const label = TYPES.find(([v]) => v === type)[1]
    setForm({ ...form, task_type: type, title: type === 'other' ? '' : label })   // title auto-fills, still editable
  }
  async function save(e) {
    e.preventDefault(); setError('')
    const body = { ...form, company: form.company || null, due_date: form.due_date || null }
    try {
      await api(form.id ? `/tasks/${form.id}/` : '/tasks/', { method: form.id ? 'PUT' : 'POST', body })
      toast(form.id ? 'Task updated' : 'Task assigned and the officer was notified'); setForm(null); tasks.reload()
    } catch (err) { setError(err.message) }
  }
  async function remove(t) {
    if (!(await confirm(`Delete the task "${t.title}"?`))) return
    await api(`/tasks/${t.id}/`, { method: 'DELETE' }); toast('Task deleted'); tasks.reload()
  }
  const firstOfficer = officers.data?.[0]?.id ?? ''

  return (
    <Page title="Assign tasks" action={!form && <button className="btn" onClick={() => setForm({ ...BLANK, assigned_to: firstOfficer })} disabled={!officers.data?.length}>New task</button>}>
      {officers.data && officers.data.length === 0 && <Alert kind="error">No verified placement officers yet. Verify an officer account first.</Alert>}
      {form && (
        <form className="card form" onSubmit={save}>
          <h3>{form.id ? 'Edit task' : 'Assign a task'}</h3>
          <Alert>{error}</Alert>
          <div className="grid2">
            <Field label="Task"><select value={form.task_type} onChange={pickType}>{TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></Field>
            <Field label="Title"><input required value={form.title} onChange={set('title')} /></Field>
            <Field label="Assign to"><select required value={form.assigned_to} onChange={set('assigned_to')}>{(officers.data || []).map((o) => <option key={o.id} value={o.id}>{o.name} – {o.details}</option>)}</select></Field>
            <Field label="Related company (optional)"><select value={form.company || ''} onChange={set('company')}><option value="">None</option>{(companies.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
            <Field label="Priority"><select value={form.priority} onChange={set('priority')}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></Field>
            <Field label="Due date"><input type="date" value={form.due_date || ''} onChange={set('due_date')} /></Field>
            {form.id && <Field label="Status"><select value={form.status} onChange={set('status')}><option value="pending">Pending</option><option value="in_progress">In progress</option><option value="completed">Completed</option></select></Field>}
          </div>
          <Field label="Instructions"><textarea rows="3" value={form.description} onChange={set('description')} /></Field>
          <div className="row"><button className="btn">{form.id ? 'Save task' : 'Assign task'}</button><button type="button" className="btn ghost" onClick={() => setForm(null)}>Cancel</button></div>
        </form>
      )}
      <div className="filters"><select value={filter} onChange={(e) => setFilter(e.target.value)}><option value="">All tasks</option><option value="pending">Pending</option><option value="in_progress">In progress</option><option value="completed">Completed</option></select></div>
      <Async state={tasks}>{(list) => list.length === 0 ? <Empty>No tasks yet. Assign the first task to a placement officer.</Empty> : (
        <div className="table-wrap"><table>
          <thead><tr><th>Task</th><th>Officer</th><th>Priority</th><th>Due</th><th>Status</th><th>Officer's note</th><th></th></tr></thead>
          <tbody>{list.map((t) => (
            <tr key={t.id}><td>{t.title}{t.company_name && <><br /><small>{t.company_name}</small></>}</td><td>{t.assigned_to_name}</td>
              <td><span className={`prio ${t.priority}`}>{t.priority}</span></td>
              <td className={t.is_overdue ? 'overdue' : ''}>{t.due_date ? fmtDate(t.due_date) : '—'}{t.is_overdue && ' (overdue)'}</td>
              <td><Badge value={t.status} /></td><td>{t.officer_note}</td>
              <td className="actions"><button className="link" onClick={() => setForm({ ...t, company: t.company || '' })}>Edit</button><button className="link danger" onClick={() => remove(t)}>Delete</button></td></tr>
          ))}</tbody>
        </table></div>
      )}</Async>
    </Page>
  )
}
