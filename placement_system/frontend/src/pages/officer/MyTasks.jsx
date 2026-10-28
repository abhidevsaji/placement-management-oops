import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { Async, Badge, Empty, Page, fmtDate, useApi, useToast } from '../../ui'

// Where each task type leads, so the officer can start straight away.
const GO = { add_company: '/companies', post_job: '/manage-jobs', set_eligibility: '/manage-jobs', review_applications: '/review', shortlist: '/review', schedule_drive: '/manage-drives', notify_students: '/manage-drives', publish_results: '/review' }

export default function MyTasks() {
  const state = useApi('/tasks/')
  const [notes, setNotes] = useState({})
  const toast = useToast()

  async function move(t, status) {
    try { await api(`/tasks/${t.id}/progress/`, { method: 'POST', body: { status, officer_note: notes[t.id] || '' } }); toast(status === 'completed' ? 'Task completed. The admin was notified.' : 'Task started'); state.reload() }
    catch (err) { toast(err.message, 'error') }
  }

  return (
    <Page title="My tasks">
      <p className="muted">Tasks assigned to you by the admin.</p>
      <Async state={state}>{(list) => list.length === 0 ? <Empty>No tasks assigned to you right now.</Empty> : (
        <div className="cards">{list.map((t) => (
          <article className={`card task ${t.priority}`} key={t.id}>
            <div className="row between"><h3>{t.title}</h3><Badge value={t.status} /></div>
            <p className="muted">From {t.assigned_by_name || 'admin'}{t.company_name && ` · ${t.company_name}`}</p>
            {t.description && <p>{t.description}</p>}
            <p><span className={`prio ${t.priority}`}>{t.priority} priority</span>{' '}
              {t.due_date && <span className={t.is_overdue ? 'overdue' : 'muted'}>Due {fmtDate(t.due_date)}{t.is_overdue && ' (overdue)'}</span>}</p>
            {t.status !== 'completed' ? (
              <>
                <input placeholder="Add a note for the admin (optional)" value={notes[t.id] || ''} onChange={(e) => setNotes({ ...notes, [t.id]: e.target.value })} />
                <div className="row">
                  {GO[t.task_type] && <Link className="btn ghost" to={GO[t.task_type]}>Go to work</Link>}
                  {t.status === 'pending' && <button className="btn ghost" onClick={() => move(t, 'in_progress')}>Start</button>}
                  <button className="btn" onClick={() => move(t, 'completed')}>Mark completed</button>
                </div>
              </>
            ) : <p className="muted">Completed{t.officer_note && `: ${t.officer_note}`}</p>}
          </article>
        ))}</div>
      )}</Async>
    </Page>
  )
}
