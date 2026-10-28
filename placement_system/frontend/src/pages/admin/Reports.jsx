import { useState } from 'react'
import { api } from '../../api'
import { Alert, Async, Empty, Page, fmtDate, useApi } from '../../ui'

const LABEL = { total_students: 'Approved students', placed_students: 'Placed students', placement_percentage: 'Placement %', companies: 'Companies', jobs: 'Jobs', applications: 'Applications', shortlisted: 'Shortlisted now' }

function ReportBody({ r }) {
  if (r.report_type === 'summary') return (
    <div className="tiles small">{Object.entries(r.data).map(([k, v]) => <div className="tile" key={k}><strong>{v}</strong><span>{LABEL[k] || k}</span></div>)}</div>
  )
  const rows = r.data.rows || []
  if (!rows.length) return <Empty>No data yet.</Empty>
  const cols = Object.keys(rows[0])
  return <div className="table-wrap"><table><thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i}>{cols.map((c) => <td key={c}>{row[c]}</td>)}</tr>)}</tbody></table></div>
}

export default function Reports() {
  const state = useApi('/reports/')
  const [open, setOpen] = useState(null)
  const [error, setError] = useState('')
  async function generate(type) {
    try { const r = await api('/reports/', { method: 'POST', body: { report_type: type } }); setOpen(r.id); state.reload() }
    catch (err) { setError(err.message) }
  }
  return (
    <Page title="Placement reports" action={<div className="row">
      <button className="btn" onClick={() => generate('summary')}>Generate summary</button>
      <button className="btn ghost" onClick={() => generate('company_wise')}>Company wise</button>
      <button className="btn ghost" onClick={() => generate('branch_wise')}>Branch wise</button>
    </div>}>
      <Alert>{error}</Alert>
      <Async state={state}>{(list) => list.length === 0 ? <Empty>No reports yet. Generate one with the buttons above.</Empty> : (
        <div className="stack">{list.map((r) => (
          <article className="card" key={r.id}>
            <button className="report-head" onClick={() => setOpen(open === r.id ? null : r.id)} aria-expanded={open === r.id}>
              <strong>{r.type_label}</strong><span className="muted">{fmtDate(r.generated_date)} by {r.generated_by_name}</span>
            </button>
            {open === r.id && <ReportBody r={r} />}
          </article>
        ))}</div>
      )}</Async>
    </Page>
  )
}
