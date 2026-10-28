import { Link } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../AuthContext'
import { Alert, Async, Empty, Page, fmtDate, useApi, useToast } from '../../ui'

export default function Jobs() {
  const state = useApi('/jobs/')
  const { user } = useAuth()
  const toast = useToast()

  async function apply(job) {
    try {
      await api(`/jobs/${job.id}/apply/`, { method: 'POST' })
      toast(`Application submitted for ${job.title} at ${job.company_name}`)
      state.reload()
    } catch (err) { toast(err.message, 'error') }
  }

  return (
    <Page title="Available jobs">
      <p className="muted">Only jobs you are eligible for are listed.</p>
      {!user.has_resume && <Alert>You need a resume before you can apply. <Link to="/profile">Upload it in My profile</Link>.</Alert>}
      <Async state={state}>{(jobs) => jobs.length === 0 ? <Empty>No open jobs match your CGPA and branch right now. Check back later.</Empty> : (
        <div className="cards">
          {jobs.map((j) => (
            <article className="card job" key={j.id}>
              <h3>{j.title}</h3>
              <p className="company">{j.company_name}</p>
              <p>{j.description}</p>
              <dl>
                <div><dt>Package</dt><dd>{j.package}</dd></div>
                <div><dt>Minimum CGPA</dt><dd>{j.min_cgpa}</dd></div>
                <div><dt>Branches</dt><dd>{j.allowed_branches || 'All'}</dd></div>
                <div><dt>Apply by</dt><dd>{fmtDate(j.last_date)}</dd></div>
              </dl>
              {j.eligibility_criteria && <p className="muted">{j.eligibility_criteria}</p>}
              <button className="btn" disabled={j.has_applied || !user.has_resume} title={!user.has_resume ? 'Upload your resume first' : ''} onClick={() => apply(j)}>{j.has_applied ? 'Applied' : 'Apply now'}</button>
            </article>
          ))}
        </div>
      )}</Async>
    </Page>
  )
}
