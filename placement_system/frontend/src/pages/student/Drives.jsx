import { Async, Badge, Empty, Page, fmtDate, useApi } from '../../ui'

export default function Drives() {
  const state = useApi('/drives/')
  return (
    <Page title="Placement drives">
      <Async state={state}>{(list) => list.length === 0 ? <Empty>No drives scheduled for your applications yet.</Empty> : (
        <div className="cards">{list.map((d) => (
          <article className="card" key={d.id}>
            <h3>{d.company_name}</h3><p className="company">{d.job_title}</p>
            <dl>
              <div><dt>Date</dt><dd>{fmtDate(d.drive_date)}</dd></div>
              <div><dt>Venue</dt><dd>{d.venue}</dd></div>
              <div><dt>Status</dt><dd><Badge value={d.status} /></dd></div>
            </dl>
            {d.description && <p className="muted">{d.description}</p>}
          </article>
        ))}</div>
      )}</Async>
    </Page>
  )
}
