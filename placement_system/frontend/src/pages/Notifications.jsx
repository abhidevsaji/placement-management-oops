import { api } from '../api'
import { Async, Empty, Page, fmtDate, useApi } from '../ui'

export default function Notifications() {
  const state = useApi('/notifications/')
  async function readAll() { await api('/notifications/read-all/', { method: 'POST' }); state.reload() }
  async function readOne(n) { if (!n.is_read) { await api(`/notifications/${n.id}/read/`, { method: 'POST' }); state.reload() } }
  return (
    <Page title="Notifications" action={<button className="btn ghost" onClick={readAll}>Mark all as read</button>}>
      <Async state={state}>{(list) => list.length === 0 ? <Empty>No notifications yet. Updates about jobs and applications will appear here.</Empty> : (
        <ul className="notes">
          {list.map((n) => (
            <li key={n.id} className={n.is_read ? '' : 'unread'} onClick={() => readOne(n)}>
              <span>{n.message}</span><time>{fmtDate(n.created_at)}</time>
            </li>
          ))}
        </ul>
      )}</Async>
    </Page>
  )
}
