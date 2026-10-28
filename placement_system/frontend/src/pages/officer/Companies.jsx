import { useState } from 'react'
import { api } from '../../api'
import { Alert, Async, Badge, Empty, Field, Page, useApi, useConfirm, useToast } from '../../ui'

const BLANK = { name: '', hr_email: '', phone: '', address: '', description: '', status: 'active' }

export default function Companies() {
  const state = useApi('/companies/')
  const confirm = useConfirm()
  const toast = useToast()
  const [form, setForm] = useState(null)   // null = form hidden
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function save(e) {
    e.preventDefault(); setError('')
    try {
      await api(form.id ? `/companies/${form.id}/` : '/companies/', { method: form.id ? 'PUT' : 'POST', body: form })
      setForm(null); state.reload()
    } catch (err) { setError(err.message) }
  }

  async function remove(c) {
    if (!(await confirm(`Delete ${c.name}? Its job postings and applications will be deleted too. Consider marking it inactive instead.`))) return
    await api(`/companies/${c.id}/`, { method: 'DELETE' }); state.reload()
  }

  return (
    <Page title="Companies" action={!form && <button className="btn" onClick={() => setForm(BLANK)}>Add company</button>}>
      {form && (
        <form className="card form" onSubmit={save}>
          <h3>{form.id ? 'Edit company' : 'Add company'}</h3>
          <Alert>{error}</Alert>
          <div className="grid2">
            <Field label="Company name"><input required value={form.name} onChange={set('name')} /></Field>
            <Field label="HR email"><input type="email" required value={form.hr_email} onChange={set('hr_email')} /></Field>
            <Field label="Phone"><input value={form.phone} onChange={set('phone')} /></Field>
            <Field label="Address"><input value={form.address} onChange={set('address')} /></Field>
            <Field label="Status"><select value={form.status} onChange={set('status')}><option value="active">Active</option><option value="inactive">Inactive</option></select></Field>
          </div>
          <Field label="Description"><textarea rows="3" value={form.description} onChange={set('description')} /></Field>
          <div className="row"><button className="btn">Save company</button><button type="button" className="btn ghost" onClick={() => setForm(null)}>Cancel</button></div>
        </form>
      )}
      <Async state={state}>{(list) => list.length === 0 ? <Empty>No companies yet. Add the first company to start posting jobs.</Empty> : (
        <div className="table-wrap"><table>
          <thead><tr><th>Name</th><th>HR contact</th><th>Phone</th><th>Open jobs</th><th>Status</th><th></th></tr></thead>
          <tbody>{list.map((c) => (
            <tr key={c.id}><td>{c.name}</td><td>{c.hr_email}</td><td>{c.phone}</td><td>{c.open_jobs}</td><td><Badge value={c.status} /></td>
              <td className="actions"><button className="link" onClick={() => setForm(c)}>Edit</button><button className="link danger" onClick={() => remove(c)}>Delete</button></td></tr>
          ))}</tbody>
        </table></div>
      )}</Async>
    </Page>
  )
}
