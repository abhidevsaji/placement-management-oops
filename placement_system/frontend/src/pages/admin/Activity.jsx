import { Async, Empty, Page, useApi } from '../../ui'

export default function Activity() {
  const state = useApi('/admin/activity/')
  return (
    <Page title="Activity log">
      <p className="muted">The latest 100 actions across the system.</p>
      <Async state={state}>{(list) => list.length === 0 ? <Empty>Nothing has happened yet.</Empty> : (
        <div className="table-wrap"><table>
          <thead><tr><th>When</th><th>User</th><th>Action</th><th>Details</th></tr></thead>
          <tbody>{list.map((l) => <tr key={l.id}><td>{new Date(l.created_at).toLocaleString('en-IN')}</td><td>{l.user_name}</td><td>{l.action.replace('_', ' ').toLowerCase()}</td><td>{l.details}</td></tr>)}</tbody>
        </table></div>
      )}</Async>
    </Page>
  )
}
