// One small helper for every call to the Django API.
const BASE = import.meta.env.VITE_API_URL || '/api'

export const getToken = () => localStorage.getItem('token')
export const setToken = (t) => (t ? localStorage.setItem('token', t) : localStorage.removeItem('token'))

// Django REST Framework returns errors in several shapes; flatten them to readable text.
export function errorText(data) {
  if (!data) return 'Something went wrong. Please try again.'
  if (typeof data === 'string') return data
  if (Array.isArray(data)) return data.join(' ')
  if (data.detail) return data.detail
  return Object.entries(data)
    .map(([k, v]) => `${k.replace('_', ' ')}: ${Array.isArray(v) ? v.join(' ') : v}`)
    .join('\n')
}

export async function api(path, { method = 'GET', body } = {}) {
  const isFile = body instanceof FormData            // file uploads: let the browser set the content type
  const headers = isFile ? {} : { 'Content-Type': 'application/json' }
  if (getToken()) headers.Authorization = `Token ${getToken()}`
  let res
  try {
    res = await fetch(`${BASE}${path}`, { method, headers, body: body ? (isFile ? body : JSON.stringify(body)) : undefined })
  } catch {
    throw Object.assign(new Error('Cannot reach the server. Is the Django backend running?'), { status: 0 })
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) {
    if (res.status === 401 && getToken()) {
      setToken(null)
      window.location.assign('/login')
    }
    throw Object.assign(new Error(errorText(data)), { status: res.status, data })
  }
  return data
}

// Resumes are private: fetch the PDF with the login token, then open it in a new tab.
export async function openPdf(path) {
  const res = await fetch(`${BASE}${path}`, { headers: { Authorization: `Token ${getToken()}` } })
  if (!res.ok) throw new Error(res.status === 404 ? 'No resume has been uploaded.' : 'Could not open the resume.')
  const url = URL.createObjectURL(await res.blob())
  window.open(url, '_blank', 'noopener')
}
