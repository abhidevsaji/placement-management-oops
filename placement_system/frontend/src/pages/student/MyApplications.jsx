import { Link } from 'react-router-dom'
import { Async, Badge, Empty, Page, Tracker, fmtDate, useApi } from '../../ui'

export default function MyApplications() {
  const state = useApi('/applications/')
  return (
    <Page title="My applications">
      <Async state={state}>{(list) => list.length === 0 ? <Empty>You have not applied yet. <Link to="/jobs">Browse available jobs</Link>.</Empty> : (
        <div className="stack">{list.map((a) => (
          <article className="card app" key={a.id}>
            <div className="row between"><div><h3>{a.job_title}</h3><p className="company">{a.company_name} · {a.package}</p></div><Badge value={a.status} /></div>
            <Tracker status={a.status} />
            <small className="muted">Applied on {fmtDate(a.applied_date)}{a.result && ` · Result published ${fmtDate(a.result.selected_date)}`}</small>
          </article>
        ))}</div>
      )}</Async>
    </Page>
  )
}
