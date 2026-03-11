import { Routes, Route, Navigate, useNavigate, NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { LayoutDashboard, Wallet, TrendingUp, Bell, LogOut, User, BarChart3, ShieldCheck } from 'lucide-react'
import './App.css'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Market from './pages/Market.jsx'
import Portfolio from './pages/Portfolio.jsx'
import AIInsights from './pages/AIInsights.jsx'
import Alerts from './pages/Alerts.jsx'
import { apiFetch, API_BASE } from './lib/api.js'
import { io } from 'socket.io-client'

function NotificationToast({ alert, onDismiss }) {
  if (!alert) return null
  return (
    <div className="notification-toast">
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        <div style={{ background: 'var(--primary)', padding: '8px', borderRadius: '50%', color: 'black' }}>
          <Bell size={18} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '2px' }}>AI Alert Triggered!</div>
          <div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.7)' }}>{alert.message}</div>
        </div>
        <button onClick={onDismiss} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', opacity: 0.5 }}>
          <LogOut size={16} style={{ transform: 'rotate(90deg)' }} />
        </button>
      </div>
    </div>
  )
}

function Layout({ children, user, onLogout }) {
  return (
    <div className="app-container">
      <aside className="sidebar">
        <div style={{ padding: '0 1rem 2rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ background: 'var(--primary)', width: 32, height: 32, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <TrendingUp size={20} color="white" />
          </div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, background: 'linear-gradient(90deg, #00d4ff, #7b2fef)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>CryptoAI</h2>
        </div>

        <nav style={{ flex: 1 }}>
          <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} end>
            <LayoutDashboard size={20} /> Dashboard
          </NavLink>
          <NavLink to="/market" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <BarChart3 size={20} /> Market
          </NavLink>
          <NavLink to="/portfolio" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Wallet size={20} /> Portfolio
          </NavLink>
          <NavLink to="/ai-insights" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <ShieldCheck size={20} /> AI Insights
          </NavLink>
          <NavLink to="/alerts" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Bell size={20} /> AI Alerts
          </NavLink>
        </nav>

        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '0 1rem', marginBottom: '1.5rem' }}>
            <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <User size={20} color="var(--text-muted)" />
            </div>
            <div style={{ overflow: 'hidden' }}>
              <p style={{ fontSize: '0.9rem', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user?.name || 'Paramesh'}</p>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user?.email || 'bhupathipramesh2025@gmail.com'}</p>
            </div>
          </div>
          <button onClick={onLogout} className="nav-link" style={{ width: '100%', border: 'none', background: 'none', cursor: 'pointer', textAlign: 'left' }}>
            <LogOut size={20} /> Logout
          </button>
        </div>
      </aside>

      <main className="main-content">
        {children}
      </main>
    </div>
  )
}

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeNotification, setActiveNotification] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (!user) return
    
    const socket = io(API_BASE.replace('/api', ''))
    socket.on('alert_notification', (alert) => {
      console.log('🔔 Alert Notification Received:', alert)
      setActiveNotification(alert)
      // Auto-hide after 10 seconds
      setTimeout(() => setActiveNotification(null), 10000)
    })

    return () => socket.disconnect()
  }, [user])

  const checkAuth = async (initialUser = null) => {
    if (initialUser) {
      setUser(initialUser)
      setLoading(false)
      return
    }
    const token = localStorage.getItem('token')
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const data = await apiFetch('/api/auth/me', { auth: true })
      console.log('Auth check success:', data)
      setUser(data)
    } catch (err) {
      console.error('Auth check failed:', err)
      // CRITICAL: Only clear session if we're explicitly unauthorized (401)
      // and the error indicates the token itself is the problem.
      if (err.status === 401) {
        const isCriticalAuthError = 
          err.message.includes('User not found') || 
          err.message.includes('Invalid token') || 
          err.message.includes('session expired');

        if (isCriticalAuthError) {
          console.warn('Session explicitly invalidated by server. Clearing token.')
          localStorage.removeItem('token')
          setUser(null)
        } else {
          // If it's a 401 but not a critical token error, we stay "logged in" 
          // but might show limited data until the server issue is resolved.
          console.warn('Unauthorized but not a critical token error. Keeping session.')
        }
      } else {
        // Network error, 500 error, etc. - NEVER log out.
        // This ensures that if the server goes down for 5 minutes, 
        // the user isn't kicked out of their session.
        console.warn('Server or network error. Preserving session state.', err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    checkAuth()
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('token')
    setUser(null)
    navigate('/login')
  }

  if (loading) return <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}>Loading...</div>

  return (
    <>
      {activeNotification && (
        <NotificationToast 
          alert={activeNotification} 
          onDismiss={() => setActiveNotification(null)} 
        />
      )}
      <Routes>
      <Route path="/login" element={!user ? <Login onLogin={checkAuth} /> : <Navigate to="/" />} />
      <Route path="/register" element={!user ? <Register /> : <Navigate to="/" />} />

      <Route path="/" element={user ? <Layout user={user} onLogout={handleLogout}><Dashboard /></Layout> : <Navigate to="/login" />} />
      <Route path="/market" element={user ? <Layout user={user} onLogout={handleLogout}><Market /></Layout> : <Navigate to="/login" />} />
      <Route path="/portfolio" element={user ? <Layout user={user} onLogout={handleLogout}><Portfolio /></Layout> : <Navigate to="/login" />} />
      <Route path="/ai-insights" element={user ? <Layout user={user} onLogout={handleLogout}><AIInsights /></Layout> : <Navigate to="/login" />} />
      <Route path="/alerts" element={user ? <Layout user={user} onLogout={handleLogout}><Alerts /></Layout> : <Navigate to="/login" />} />

      <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}
