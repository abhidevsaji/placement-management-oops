import { useEffect, useRef, useState } from 'react'
import { Navigate, NavLink, Outlet, Route, Routes } from 'react-router-dom'
import { api } from './api'
import { useAuth } from './AuthContext'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Profile from './pages/Profile'
import Notifications from './pages/Notifications'
import Jobs from './pages/student/Jobs'
import MyApplications from './pages/student/MyApplications'
import Drives from './pages/student/Drives'
import Companies from './pages/officer/Companies'
import ManageJobs from './pages/officer/ManageJobs'
import Applications from './pages/officer/Applications'
import ManageDrives from './pages/officer/ManageDrives'
import Placed from './pages/officer/Placed'
import Verification from './pages/admin/Verification'
import AdminTasks from './pages/admin/Tasks'
import MyTasks from './pages/officer/MyTasks'
import Reports from './pages/admin/Reports'
import Activity from './pages/admin/Activity'
import { useToast } from './ui'

// Menu items per role (role-based UI; the real protection is in the Django API).
const MENUS = {
  student: [['/', 'Dashboard'], ['/jobs', 'Available jobs'], ['/applications', 'My applications'], ['/drives', 'Placement drives'], ['/notifications', 'Notifications'], ['/profile', 'My profile']],
  officer: [['/', 'Dashboard'], ['/tasks', 'My tasks'], ['/companies', 'Companies'], ['/manage-jobs', 'Job postings'], ['/review', 'Applications'], ['/manage-drives', 'Placement drives'], ['/placed', 'Placed students'], ['/notifications', 'Notifications'], ['/profile', 'My profile']],
  admin: [['/', 'Dashboard'], ['/verify', 'Verify accounts'], ['/tasks', 'Assign tasks'], ['/companies', 'Companies'], ['/manage-jobs', 'Job postings'], ['/placed', 'Placed students'], ['/reports', 'Reports'], ['/activity', 'Activity log'], ['/profile', 'My profile']],
}
const ROLE_LABEL = { student: 'Student', officer: 'Placement Officer', admin: 'Admin' }

function Shell() {
  const { user, logout } = useAuth()
  const [counts, setCounts] = useState({})
  const toast = useToast()
  const lastUnread = useRef(null)
  // Refresh the menu badges every 20 seconds and pop up a toast when something new arrives.
  useEffect(() => {
    const load = () => api('/dashboard/').then((d) => {
      if (lastUnread.current !== null && d.unread_notifications > lastUnread.current) toast('You have a new notification')
      lastUnread.current = d.unread_notifications || 0
      setCounts(d)
    }).catch(() => {})
    load()
    const timer = setInterval(load, 20000)
    return () => clearInterval(timer)
  }, [toast])
  const badge = { '/notifications': counts.unread_notifications, '/verify': counts.pending_users, '/tasks': counts.open_tasks }
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">Campus Placement Portal</div>
        <nav>
          {MENUS[user.role].map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'}>
              {label}
              {badge[to] > 0 && <b className="count">{badge[to]}</b>}
            </NavLink>
          ))}
        </nav>
        <div className="who">
          <strong>{user.name}</strong>
          <span>{ROLE_LABEL[user.role]}</span>
          <button className="link" onClick={logout}>Log out</button>
        </div>
      </aside>
      <main className="main"><Outlet /></main>
    </div>
  )
}

// Only lets the listed roles open a route.
function RoleRoute({ roles, children }) {
  const { user } = useAuth()
  return roles.includes(user.role) ? children : <Navigate to="/" replace />
}

function Protected() {
  const { user, loading } = useAuth()
  if (loading) return <p className="empty">Loading…</p>
  return user ? <Shell /> : <Navigate to="/login" replace />
}

// Same address, different page: the admin assigns tasks, the officer works on them.
function TasksByRole() {
  const { user } = useAuth()
  return user.role === 'admin' ? <AdminTasks /> : <MyTasks />
}

const ST = ['student'], PO = ['officer'], AD = ['admin'], PA = ['officer', 'admin']

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<Protected />}>
        <Route index element={<Dashboard />} />
        <Route path="profile" element={<Profile />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="jobs" element={<RoleRoute roles={ST}><Jobs /></RoleRoute>} />
        <Route path="applications" element={<RoleRoute roles={ST}><MyApplications /></RoleRoute>} />
        <Route path="drives" element={<RoleRoute roles={ST}><Drives /></RoleRoute>} />
        <Route path="companies" element={<RoleRoute roles={PA}><Companies /></RoleRoute>} />
        <Route path="manage-jobs" element={<RoleRoute roles={PA}><ManageJobs /></RoleRoute>} />
        <Route path="review" element={<RoleRoute roles={PO}><Applications /></RoleRoute>} />
        <Route path="manage-drives" element={<RoleRoute roles={PO}><ManageDrives /></RoleRoute>} />
        <Route path="placed" element={<RoleRoute roles={PA}><Placed /></RoleRoute>} />
        <Route path="verify" element={<RoleRoute roles={AD}><Verification /></RoleRoute>} />
        <Route path="tasks" element={<RoleRoute roles={PA}>{<TasksByRole />}</RoleRoute>} />
        <Route path="reports" element={<RoleRoute roles={AD}><Reports /></RoleRoute>} />
        <Route path="activity" element={<RoleRoute roles={AD}><Activity /></RoleRoute>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
