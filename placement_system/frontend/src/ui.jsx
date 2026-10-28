import { useCallback, useEffect, useState } from 'react'
import { api } from './api'

// Load data from the API: const { data, error, loading, reload } = useApi('/jobs/')
export function useApi(path) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const reload = useCallback(() => {
    setLoading(true)
    api(path).then((d) => { setData(d); setError('') }).catch((e) => setError(e.message)).finally(() => setLoading(false))
  }, [path])
  useEffect(() => { reload() }, [reload])
  return { data, error, loading, reload }
}

export const Page = ({ title, action, children }) => (
  <section>
    <div className="page-head"><h1>{title}</h1>{action}</div>
    {children}
  </section>
)

export const Alert = ({ kind = 'error', children }) =>
  children ? <div className={`alert ${kind}`} role={kind === 'error' ? 'alert' : 'status'}>{children}</div> : null

export const Empty = ({ children }) => <p className="empty">{children}</p>

export const Loading = () => <p className="empty">Loading…</p>

export const Badge = ({ value }) => <span className={`badge ${value}`}>{String(value).replace('_', ' ')}</span>

export function Field({ label, children, hint }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  )
}

// Wraps a data page: shows loading / error, then renders children(data).
export function Async({ state, children }) {
  if (state.loading && !state.data) return <Loading />
  if (state.error) return <Alert>{state.error}</Alert>
  return children(state.data)
}

export const fmtDate = (d) => (d ? new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : '')

// ---------- interactive building blocks ----------
import { createContext, useContext, useRef } from 'react'

const ToastContext = createContext(() => {})
export const useToast = () => useContext(ToastContext)

// Small pop-up messages: const toast = useToast(); toast('Saved'); toast('Failed', 'error')
export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const id = useRef(0)
  const push = useCallback((text, kind = 'success') => {
    const key = ++id.current
    setItems((list) => [...list, { key, text, kind }])
    setTimeout(() => setItems((list) => list.filter((t) => t.key !== key)), 4000)
  }, [])
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toasts" aria-live="polite">
        {items.map((t) => <div key={t.key} className={`toast ${t.kind}`}>{t.text}</div>)}
      </div>
    </ToastContext.Provider>
  )
}

export function Modal({ title, onClose, children, wide }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? 'wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head"><h3>{title}</h3><button className="link" onClick={onClose} aria-label="Close">Close</button></div>
        {children}
      </div>
    </div>
  )
}

const ConfirmContext = createContext(() => Promise.resolve(true))
export const useConfirm = () => useContext(ConfirmContext)

// const confirm = useConfirm();  if (!(await confirm('Delete this?'))) return
export function ConfirmProvider({ children }) {
  const [ask, setAsk] = useState(null)
  const confirm = useCallback((message) => new Promise((resolve) => setAsk({ message, resolve })), [])
  const answer = (v) => { ask.resolve(v); setAsk(null) }
  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {ask && (
        <Modal title="Are you sure?" onClose={() => answer(false)}>
          <p>{ask.message}</p>
          <div className="row"><button className="btn danger" onClick={() => answer(true)}>Yes, continue</button><button className="btn ghost" onClick={() => answer(false)}>Cancel</button></div>
        </Modal>
      )}
    </ConfirmContext.Provider>
  )
}

// Horizontal bars: items = [[label, value, tone]]
export function Bars({ items }) {
  const max = Math.max(1, ...items.map((i) => i[1]))
  return (
    <div className="bars">
      {items.map(([label, value, tone]) => (
        <div className="bar-row" key={label}>
          <span>{label}</span>
          <div className="bar-track"><div className={`bar-fill ${tone || ''}`} style={{ width: `${(value / max) * 100}%` }} /></div>
          <b>{value}</b>
        </div>
      ))}
    </div>
  )
}

// Application progress: Applied -> Shortlisted -> Placed (or Rejected)
export function Tracker({ status }) {
  const rejected = status === 'rejected'
  const steps = ['applied', 'shortlisted', rejected ? 'rejected' : 'placed']
  const at = steps.indexOf(status)
  return (
    <ol className="tracker" aria-label={`Status: ${status}`}>
      {steps.map((s, i) => <li key={s} className={`${i <= at ? 'done' : ''} ${i === at ? 'now' : ''} ${s === 'rejected' ? 'bad' : ''}`}><i />{s}</li>)}
    </ol>
  )
}

export const Tabs = ({ value, onChange, options }) => (
  <div className="tabs" role="tablist">
    {options.map(([v, label, n]) => (
      <button type="button" key={v} role="tab" aria-selected={value === v} className={value === v ? 'on' : ''} onClick={() => onChange(v)}>
        {label}{n > 0 && <b className="count">{n}</b>}
      </button>
    ))}
  </div>
)
