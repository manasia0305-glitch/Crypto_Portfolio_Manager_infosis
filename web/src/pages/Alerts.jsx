import { useState, useEffect } from 'react'
import { apiFetch } from '../lib/api.js'
import { Bell, Trash2, Plus, AlertCircle, TrendingUp, TrendingDown, Clock, ShieldCheck } from 'lucide-react'

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [marketData, setMarketData] = useState([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [alertForm, setAlertForm] = useState({
    coin_id: 'bitcoin',
    alert_type: 'price_above',
    threshold: ''
  })

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const data = await apiFetch('/api/alerts', { auth: true })
        setAlerts(data.data || [])
      } catch (err) {
        console.error('Error fetching alerts:', err)
      }
    }

    const fetchMarketData = async () => {
      try {
        const data = await apiFetch('/api/market?per_page=50')
        setMarketData(data.data || [])
        if (data.data?.length > 0 && !alertForm.coin_id) {
          setAlertForm(prev => ({ ...prev, coin_id: data.data[0].coin_id }))
        }
      } catch (err) {
        console.error('Error fetching market data:', err)
      }
    }

    const init = async () => {
      await Promise.all([fetchAlerts(), fetchMarketData()])
      setLoading(false)
    }
    init()
  }, [])

  const handleCreateAlert = async (e) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      await apiFetch('/api/alerts', {
        method: 'POST',
        body: {
          ...alertForm,
          threshold: parseFloat(alertForm.threshold)
        },
        auth: true
      })
      setIsModalOpen(false)
      setAlertForm({ ...alertForm, threshold: '' })
      fetchAlerts()
    } catch (err) {
      alert('Failed to create alert: ' + err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDeleteAlert = async (alertId) => {
    if (!window.confirm('Are you sure you want to remove this alert?')) return
    try {
      await apiFetch(`/api/alerts/${alertId}`, { method: 'DELETE', auth: true })
      fetchAlerts()
    } catch (err) {
      alert('Failed to delete alert: ' + err.message)
    }
  }

  if (loading) return <div className="loader-container">Loading alerts...</div>

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', paddingBottom: '4rem' }}>
      <header style={{ marginBottom: '2.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '2.4rem', fontWeight: 800, marginBottom: '0.4rem' }}>AI Alerts</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>Smart notifications for price movements and risk events.</p>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="btn"
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px', 
            padding: '0.8rem 1.5rem', 
            borderRadius: '12px',
            background: 'linear-gradient(90deg, var(--primary), var(--secondary))',
            color: 'black',
            fontWeight: 700
          }}
        >
          <Plus size={20} /> Create Alert
        </button>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
        {alerts.length === 0 ? (
          <div className="card" style={{ 
            gridColumn: '1 / -1', 
            padding: '5rem 2rem', 
            textAlign: 'center',
            background: 'rgba(13, 27, 42, 0.4)',
            border: '1px dashed var(--border)',
            borderRadius: '24px'
          }}>
            <Bell size={48} color="var(--text-muted)" style={{ marginBottom: '1.5rem', opacity: 0.5 }} />
            <h3 style={{ fontSize: '1.4rem', marginBottom: '0.5rem' }}>No active alerts</h3>
            <p style={{ color: 'var(--text-muted)' }}>You haven't set any AI alerts yet. Create one to stay ahead of the market.</p>
          </div>
        ) : (
          alerts.map(alert => (
            <div key={alert.id} className="card" style={{ padding: '1.5rem', borderRadius: '20px', border: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ 
                    width: 40, 
                    height: 40, 
                    borderRadius: '12px', 
                    background: 'rgba(0, 212, 255, 0.1)', 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center' 
                  }}>
                    <Bell size={20} color="var(--primary)" />
                  </div>
                  <div>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>{alert.coin_id.toUpperCase()}</h3>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>PRICE ALERT</span>
                  </div>
                </div>
                <button 
                  onClick={() => handleDeleteAlert(alert.id)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                >
                  <Trash2 size={18} />
                </button>
              </div>

              <div style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.2rem', fontWeight: 700, marginBottom: '4px' }}>
                  {alert.alert_type === 'price_above' ? <TrendingUp size={18} color="var(--positive)" /> : <TrendingDown size={18} color="var(--negative)" />}
                  {alert.alert_type === 'price_above' ? 'Price Above' : 'Price Below'}
                  <span style={{ color: 'var(--primary)' }}>${alert.threshold.toLocaleString()}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  <Clock size={14} />
                  Created {new Date(alert.created_at || Date.now()).toLocaleDateString()}
                </div>
              </div>

              <div style={{ 
                padding: '0.8rem', 
                background: alert.is_active ? 'rgba(0, 230, 118, 0.05)' : 'rgba(255, 23, 68, 0.05)', 
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '0.85rem',
                fontWeight: 600,
                color: alert.is_active ? 'var(--positive)' : 'var(--negative)'
              }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: alert.is_active ? 'var(--positive)' : 'var(--negative)' }} />
                {alert.is_active ? 'Actively Monitoring' : 'Triggered / Inactive'}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Create Alert Modal */}
      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '450px' }}>
            <h2 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Bell size={24} color="var(--primary)" />
              Create AI Alert
            </h2>
            
            <form onSubmit={handleCreateAlert}>
              <div style={{ marginBottom: '1.2rem' }}>
                <label className="form-label">Select Asset</label>
                <select 
                  className="form-input"
                  value={alertForm.coin_id}
                  onChange={(e) => setAlertForm({ ...alertForm, coin_id: e.target.value })}
                >
                  {marketData.map(coin => (
                    <option key={coin.coin_id} value={coin.coin_id}>
                      {coin.name} ({coin.symbol.toUpperCase()})
                    </option>
                  ))}
                </select>
              </div>
              
              <div style={{ marginBottom: '1.2rem' }}>
                <label className="form-label">Alert Type</label>
                <select 
                  className="form-input"
                  value={alertForm.alert_type}
                  onChange={(e) => setAlertForm({ ...alertForm, alert_type: e.target.value })}
                >
                  <option value="price_above">Price goes above</option>
                  <option value="price_below">Price goes below</option>
                </select>
              </div>
              
              <div style={{ marginBottom: '2rem' }}>
                <label className="form-label">Price Threshold (USD)</label>
                <input 
                  type="number" 
                  step="any"
                  className="form-input"
                  placeholder="e.g. 75000"
                  value={alertForm.threshold}
                  onChange={(e) => setAlertForm({ ...alertForm, threshold: e.target.value })}
                  required
                />
              </div>
              
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button 
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsModalOpen(false)}
                  style={{ flex: 1 }}
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={isSubmitting}
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                >
                  {isSubmitting ? 'Creating...' : 'Set Alert'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
