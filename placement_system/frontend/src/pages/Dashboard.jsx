import { Link } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { Async, Bars, Page, useApi } from '../ui'

// Which numbers to show for each role, and where each one leads.
const TILES = {
  student: [['applications_total', 'Applications', '/applications'], ['shortlisted', 'Shortlisted', '/applications'], ['placed', 'Placed', '/applications'], ['unread_notifications', 'Unread notifications', '/notifications']],
  officer: [['open_tasks', 'Open tasks from admin', '/tasks'], ['pending_review', 'Awaiting review', '/review'], ['shortlisted', 'Shortlisted', '/review'], ['placed', 'Placed students', '/placed'], ['open_jobs', 'Open jobs', '/manage-jobs'], ['companies', 'Companies', '/companies']],
  admin: [['pending_users', 'Accounts to verify', '/verify'], ['open_tasks', 'Open officer tasks', '/tasks'], ['overdue_tasks', 'Overdue tasks', '/tasks'], ['students', 'Students', '/verify'], ['officers', 'Placement officers', '/verify'], ['recent_activity', 'Logged activities', '/activity']],
}
const CHARTS = {
  student: (d) => [['Applied', d.applied, ''], ['Shortlisted', d.shortlisted, 'warn'], ['Placed', d.placed, 'ok'], ['Rejected', d.rejected, 'bad']],
  officer: (d) => [['Awaiting review', d.pending_review, ''], ['Shortlisted', d.shortlisted, 'warn'], ['Placed', d.placed, 'ok']],
}

export default function Dashboard() {
  const { user } = useAuth()
  const state = useApi('/dashboard/')
  return (
    <Page title={`Welcome, ${user.name.split(' ')[0]}`}>
      <Async state={state}>{(d) => (
        <>
          {user.role === 'student' && !user.has_resume && (
            <div className="alert error">You have not uploaded a resume yet. <Link to="/profile">Upload it now</Link> to start applying.</div>
          )}
          <div className="tiles">
            {TILES[user.role].map(([key, label, to]) => (
              <Link to={to} className={`tile ${key === 'overdue_tasks' && d[key] > 0 ? 'alarm' : ''}`} key={key}><strong>{d[key] ?? 0}</strong><span>{label}</span></Link>
            ))}
          </div>
          {CHARTS[user.role] && (
            <div className="card" style={{ marginTop: '1rem' }}>
              <h3>{user.role === 'student' ? 'Where your applications stand' : 'Application pipeline'}</h3>
              <Bars items={CHARTS[user.role](d)} />
            </div>
          )}
        </>
      )}</Async>
    </Page>
  )
}
