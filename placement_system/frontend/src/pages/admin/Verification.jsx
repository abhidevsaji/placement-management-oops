import { useState } from 'react'
import { api, openPdf } from '../../api'
import { Alert, Async, Badge, Empty, Field, Modal, Page, Tabs, fmtDate, useApi, useConfirm, useToast } from '../../ui'

// Admin reviews each registration before the account can be used.
export default function Verification() {
  const [role, setRole] = useState('student')
  const [status, setStatus] = useState('pending')
  const [q, setQ] = useState('')
  const query = new URLSearchParams({ role, ...(status && { status }), ...(q && { q }) }).toString()
  const state = useApi(`/admin/users/?${query}`)
  const counts = useApi('/dashboard/')
  const [review, setReview] = useState(null)   // user detail shown in the modal
  const toast = useToast()
  const confirm = useConfirm()

  async function open(u) { setReview(await api(`/admin/users/${u.id}/`)) }
  async function remove(u) {
    if (!(await confirm(`Delete ${u.name}? Their applications and data are removed too.`))) return
    await api(`/admin/users/${u.id}/`, { method: 'DELETE' }); toast('User deleted'); state.reload(); counts.reload()
  }
  const done = (msg) => { setReview(null); toast(msg); state.reload(); counts.reload() }

  return (
    <Page title="Verify accounts">
      <Tabs value={role} onChange={setRole} options={[['student', 'Students'], ['officer', 'Placement officers']]} />
      <div className="filters">
        <input placeholder="Search name or email" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="pending">Waiting for verification</option><option value="approved">Verified</option><option value="rejected">Rejected</option><option value="">All</option>
        </select>
      </div>
      <Async state={state}>{(list) => list.length === 0 ? <Empty>{status === 'pending' ? 'No accounts are waiting for verification.' : 'No users match these filters.'}</Empty> : (
        <div className="table-wrap"><table>
          <thead><tr><th>Name</th><th>Email</th><th>Details</th>{role === 'student' && <th>Resume</th>}<th>Registered</th><th>Status</th><th></th></tr></thead>
          <tbody>{list.map((u) => (
            <tr key={u.id}><td>{u.name}</td><td>{u.email}</td><td>{u.details}</td>
              {role === 'student' && <td>{u.has_resume ? 'Uploaded' : <span className="muted">None</span>}</td>}
              <td>{fmtDate(u.date_joined)}</td><td><Badge value={u.status} /></td>
              <td className="actions"><button className="link" onClick={() => open(u)}>{u.status === 'pending' ? 'Review' : 'View'}</button><button className="link danger" onClick={() => remove(u)}>Delete</button></td></tr>
          ))}</tbody>
        </table></div>
      )}</Async>
      {review && <ReviewModal u={review} onClose={() => setReview(null)} onDone={done} />}
    </Page>
  )
}

function ReviewModal({ u, onClose, onDone }) {
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const p = u.profile
  const rows = u.role === 'student'
    ? [['Roll number', p.roll_no], ['Branch', p.branch], ['CGPA', p.cgpa], ['Phone', p.phone], ['Address', p.address || '—']]
    : [['Department', p.department], ['Phone', p.phone]]

  async function act(action) {
    try {
      await api(`/admin/users/${u.id}/${action}/`, { method: 'POST', body: action === 'reject' ? { reason } : undefined })
      onDone(action === 'approve' ? `${u.name} is verified` : `${u.name} was rejected`)
    } catch (err) { setError(err.message) }
  }
  return (
    <Modal title={`Review: ${u.name}`} onClose={onClose}>
      <Alert>{error}</Alert>
      <dl><div><dt>Email</dt><dd>{u.email}</dd></div><div><dt>Status</dt><dd><Badge value={u.status} /></dd></div>
        {rows.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
      {u.role === 'student' && (
        <p>{u.has_resume ? <button className="btn ghost" onClick={() => openPdf(`/students/${u.id}/resume/`).catch((e) => setError(e.message))}>Open resume (PDF)</button> : <span className="muted">No resume uploaded yet.</span>}</p>
      )}
      {u.rejection_reason && <Alert>Rejected: {u.rejection_reason}</Alert>}
      {u.verified_at && <p className="muted">Reviewed on {fmtDate(u.verified_at)} by {u.verified_by_name || 'admin'}.</p>}
      {rejecting ? (
        <>
          <Field label="Reason for rejection" hint="The user will see this when they try to log in."><textarea rows="2" value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
          <div className="row"><button className="btn danger" onClick={() => act('reject')}>Reject account</button><button className="btn ghost" onClick={() => setRejecting(false)}>Back</button></div>
        </>
      ) : (
        <div className="row">
          {u.status !== 'approved' && <button className="btn" onClick={() => act('approve')}>Verify and approve</button>}
          {u.status === 'pending' && <button className="btn ghost" onClick={() => setRejecting(true)}>Reject…</button>}
        </div>
      )}
    </Modal>
  )
}
