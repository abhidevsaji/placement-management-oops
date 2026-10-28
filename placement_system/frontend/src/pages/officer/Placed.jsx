import { Async, Empty, Page, fmtDate, useApi } from '../../ui'

export default function Placed() {
  const state = useApi('/placed-students/')
  return (
    <Page title="Placed students">
      <Async state={state}>{(list) => list.length === 0 ? <Empty>No students have been placed yet.</Empty> : (
        <div className="table-wrap"><table>
          <thead><tr><th>Student</th><th>Roll no.</th><th>Branch</th><th>Company</th><th>Role</th><th>Package</th><th>Selected on</th></tr></thead>
          <tbody>{list.map((a) => (
            <tr key={a.id}><td>{a.student_name}</td><td>{a.roll_no}</td><td>{a.branch}</td><td>{a.company_name}</td><td>{a.job_title}</td><td>{a.package}</td><td>{fmtDate(a.result?.selected_date)}</td></tr>
          ))}</tbody>
        </table></div>
      )}</Async>
    </Page>
  )
}
