import { useState, useEffect, useMemo } from 'react'
import { apiFetch, API_BASE } from '../lib/api.js'
import { TrendingUp, TrendingDown, Search, Filter, Grid3X3, List as ListIcon, Info, Sparkles, ChevronRight, MessageSquare, Star, Bell, X } from 'lucide-react'
import MarketHeatmap from '../components/MarketHeatmap.jsx'
import { io } from 'socket.io-client'

// Simple Sparkline component using SVG
const Sparkline = ({ data, color }) => {
  if (!data || data.length === 0) return null
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min
  const width = 100
  const height = 40
  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * width
    const y = height - ((val - min) / (range || 1)) * height
    return `${x},${y}`
  }).join(' ')

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  )
}

const MarketStatCard = ({ title, value, change, classification, type = 'default' }) => {
  const getGauge = () => {
    if (title === 'Fear & Greed') {
      return (
        <div style={{ marginTop: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
            <span style={{ color: 'var(--text-main)' }}>{classification}</span>
            <span style={{ color: 'var(--text-muted)' }}>{value}</span>
          </div>
          <div className="fng-gauge">
            <div className="fng-gauge-fill" style={{ width: '100%' }}></div>
            <div className="fng-pointer" style={{ left: `${value}%` }}></div>
          </div>
        </div>
      )
    }
    if (title === 'Altcoin Season') {
      const val = parseInt(value) || 0
      return (
        <div style={{ marginTop: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
            <span style={{ color: 'var(--text-main)' }}>{classification}</span>
            <span style={{ color: 'var(--text-muted)' }}>{value}</span>
          </div>
          <div className="alt-season-gauge">
            <div className="alt-season-fill" style={{ width: `${val}%` }}></div>
          </div>
        </div>
      )
    }
    if (title === 'Average RSI') {
      const val = parseFloat(value) || 0
      return (
        <div style={{ marginTop: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
            <span style={{ color: 'var(--text-main)' }}>{classification}</span>
            <span style={{ color: 'var(--text-muted)' }}>{value}</span>
          </div>
          <div className="rsi-gauge">
            <div className="rsi-fill" style={{ width: '100%' }}></div>
            <div className="fng-pointer" style={{ left: `${val}%` }}></div>
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <div className="market-stat-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 500 }}>{title}</span>
        <ChevronRight size={14} color="var(--text-muted)" />
      </div>
      <div style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '6px' }}>
        {title === 'Market Cap' ? value : value.toString().split('/')[0]}
      </div>
      {change !== undefined && (
        <div style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600 }} className={change >= 0 ? 'positive' : 'negative'}>
          {change >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          {Math.abs(change).toFixed(2)}%
        </div>
      )}
      {getGauge()}
    </div>
  )
}

export default function Market() {
  const [marketData, setMarketData] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [viewMode, setViewMode] = useState('list')
  const [category, setCategory] = useState('All')
  const [watchlist, setWatchlist] = useState(() => {
    const saved = localStorage.getItem('crypto_watchlist')
    return saved ? JSON.parse(saved) : []
  })
  
  // Alert Modal State
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false)
  const [activeAlerts, setActiveAlerts] = useState([])
  const [alertForm, setAlertForm] = useState({
    coin_id: 'bitcoin',
    alert_type: 'price_above',
    threshold: ''
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  // AI Chat State
  const [chatMessage, setChatMessage] = useState('')
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [chatHistory, setChatHistory] = useState([
    { type: 'ai', text: "Hello! I'm your AI Market Assistant. Ask me anything about current prices, predictions, or your portfolio performance." }
  ])
  const [isChatLoading, setIsChatLoading] = useState(false)

  const categories = ['All', 'Trending', 'Watchlist', 'Prediction Markets', 'Most Visited', 'New', 'Solana', 'Ethereum', 'Base', 'BSC']

  const fetchAlerts = async () => {
    try {
      const data = await apiFetch('/api/alerts', { auth: true })
      setActiveAlerts(data.data || [])
    } catch (err) {
      console.error('Error fetching alerts:', err)
    }
  }

  const handleDeleteAlert = async (alertId) => {
    if (!window.confirm('Are you sure you want to remove this alert?')) return
    try {
      await apiFetch(`/api/alerts/${alertId}`, { method: 'DELETE', auth: true })
      fetchAlerts()
    } catch (err) {
      console.error('Error deleting alert:', err)
      alert('Failed to delete alert: ' + err.message)
    }
  }

  const handleChatSubmit = async (e, forcedMsg = null) => {
    if (e && e.key !== 'Enter' && !forcedMsg) return
    
    const userMsg = (forcedMsg || chatMessage).trim()
    if (!userMsg || isChatLoading) return

    setChatMessage('')
    setChatHistory(prev => [...prev, { type: 'user', text: userMsg }])
    setIsChatLoading(true)
    setIsChatOpen(true)

    try {
      const data = await apiFetch('/api/ai/chat', {
        method: 'POST',
        body: { message: userMsg },
        auth: true
      })
      setChatHistory(prev => [...prev, { type: 'ai', text: data.response }])
    } catch (err) {
      console.error('AI chat error:', err)
      setChatHistory(prev => [...prev, { type: 'ai', text: "Sorry, I'm having trouble connecting to the market brain. Please try again in a moment." }])
    } finally {
      setIsChatLoading(false)
    }
  }

  useEffect(() => {
    localStorage.setItem('crypto_watchlist', JSON.stringify(watchlist))
  }, [watchlist])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [mData, sData, aData] = await Promise.all([
          apiFetch('/api/market?per_page=50'),
          apiFetch('/api/market/summary'),
          apiFetch('/api/alerts', { auth: true })
        ])
        setMarketData(mData.data || [])
        setSummary(sData.data || null)
        setActiveAlerts(aData.data || [])
        
        // Default alert coin if data exists
        if (mData.data?.length > 0) {
          setAlertForm(prev => ({ ...prev, coin_id: mData.data[0].coin_id }))
        }
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()

    const socket = io(API_BASE.replace('/api', ''))
    socket.on('market_update', (newData) => {
      setMarketData(prev => {
        const updated = [...prev]
        newData.forEach(coin => {
          const index = updated.findIndex(c => c.coin_id === (coin.id || coin.coin_id))
          if (index !== -1) {
            updated[index] = { ...updated[index], ...coin }
          }
        })
        return updated
      })
    })

    return () => socket.disconnect()
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
      alert(`Alert created successfully for ${alertForm.coin_id}!`)
      setIsAlertModalOpen(false)
      fetchAlerts() // Refresh the list
    } catch (err) {
      console.error('Alert creation error:', err)
      if (err.status === 401) {
        alert('Session expired. Please log in again.')
        localStorage.removeItem('token')
        window.location.href = '/login' // Force redirect to login
      } else {
        alert('Failed to create alert: ' + err.message)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const toggleWatchlist = (coinId) => {
    setWatchlist(prev => 
      prev.includes(coinId) 
        ? prev.filter(id => id !== coinId) 
        : [...prev, coinId]
    )
  }

  const formatLargeNumber = (num) => {
    if (!num) return '$0'
    if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`
    return `$${num.toLocaleString()}`
  }

  const filteredData = useMemo(() => {
    let data = [...marketData]

    // Category Filtering
    if (category === 'Trending') {
      data = data.sort((a, b) => (b.total_volume || 0) - (a.total_volume || 0)).slice(0, 15)
    } else if (category === 'Watchlist') {
      data = data.filter(coin => watchlist.includes(coin.coin_id))
    } else if (category === 'Prediction Markets') {
      const predCoins = ['bitcoin', 'ethereum', 'cardano', 'solana', 'binancecoin']
      data = data.filter(coin => predCoins.includes(coin.coin_id))
    } else if (category === 'Most Visited') {
      data = data.filter(coin => coin.market_cap_rank <= 10)
    } else if (category === 'New') {
      data = data.filter(coin => coin.market_cap_rank > 40 || !coin.market_cap_rank)
    } else if (category === 'Solana') {
      const solanaRelated = ['solana', 'raydium', 'serum', 'jupiter-exchange', 'bonk', 'pyth-network']
      data = data.filter(coin => solanaRelated.includes(coin.coin_id) || coin.symbol === 'sol')
    } else if (category === 'Ethereum') {
      const ethRelated = ['ethereum', 'uniswap', 'aave', 'chainlink', 'lido-dao', 'maker']
      data = data.filter(coin => ethRelated.includes(coin.coin_id) || coin.symbol === 'eth')
    } else if (category === 'Base') {
      const baseRelated = ['coinbase-wrapped-staked-eth', 'aerodrome-finance', 'base-native']
      data = data.filter(coin => baseRelated.includes(coin.coin_id))
    } else if (category === 'BSC') {
      const bscRelated = ['binancecoin', 'pancakeswap', 'venus', 'alpaca-finance']
      data = data.filter(coin => bscRelated.includes(coin.coin_id) || coin.symbol === 'bnb')
    }

    // Search Filtering
    if (search) {
      data = data.filter(coin => 
        coin.name.toLowerCase().includes(search.toLowerCase()) || 
        coin.symbol.toLowerCase().includes(search.toLowerCase())
      )
    }

    return data
  }, [marketData, category, search, watchlist])

  if (loading) return <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>Loading market data...</div>

  return (
    <div style={{ paddingBottom: '4rem' }}>
      {/* Top Stats */}
      <div style={{ display: 'flex', gap: '1rem', overflowX: 'auto', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
        <MarketStatCard 
          title="Market Cap" 
          value={formatLargeNumber(summary?.market_cap)} 
          change={summary?.market_cap_change} 
        />
        <MarketStatCard 
          title="Fear & Greed" 
          value={summary?.fear_and_greed?.value || 50} 
          classification={summary?.fear_and_greed?.value_classification || 'Neutral'}
        />
        <MarketStatCard 
          title="Altcoin Season" 
          value={summary?.altcoin_season?.value || "50/100"} 
          classification={summary?.altcoin_season?.label || "Neutral"}
        />
        <MarketStatCard 
          title="Average RSI" 
          value={summary?.avg_rsi?.value || "50.00"} 
          classification={summary?.avg_rsi?.label || "Neutral"}
        />
      </div>

      {/* Alert Ticker */}
      <div style={{ 
        background: 'rgba(0, 212, 255, 0.05)', 
        border: '1px solid var(--border)', 
        borderRadius: '12px', 
        padding: '0.8rem 1.2rem', 
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        fontSize: '0.9rem'
      }}>
        <div style={{ background: 'var(--primary)', color: 'black', padding: '3px 10px', borderRadius: '6px', fontWeight: 800, fontSize: '0.75rem', letterSpacing: '0.5px' }}>NEW</div>
        <p style={{ flex: 1, color: 'var(--text-main)', fontWeight: 500 }}>Bitcoin ETFs see $349M single-day outflows as market corrects.</p>
        <div 
          onClick={() => setIsAlertModalOpen(true)}
          style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', color: 'var(--primary)', fontWeight: 600 }}
        >
          <Sparkles size={16} />
          <span>Add AI alert</span>
        </div>
      </div>

      {/* Active Alerts List */}
      {activeAlerts.length > 0 && (
        <div style={{ 
          display: 'flex', 
          gap: '12px', 
          overflowX: 'auto', 
          paddingBottom: '1.5rem',
          scrollbarWidth: 'none',
          msOverflowStyle: 'none'
        }}>
          {activeAlerts.map(alert => (
            <div key={alert._id} style={{
              background: 'rgba(123, 47, 239, 0.05)',
              border: '1px solid rgba(123, 47, 239, 0.2)',
              borderRadius: '12px',
              padding: '0.6rem 1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              whiteSpace: 'nowrap',
              fontSize: '0.85rem'
            }}>
              <Bell size={14} color="var(--secondary)" />
              <span>{alert.coin_id.toUpperCase()} {alert.alert_type === 'price_above' ? '≥' : '≤'} ${alert.threshold.toLocaleString()}</span>
              <div 
                style={{ width: 8, height: 8, borderRadius: '50%', background: alert.is_active ? '#00e676' : '#ff1744' }}
                title={alert.is_active ? 'Monitoring' : 'Triggered'}
              ></div>
              <X 
                size={14} 
                style={{ cursor: 'pointer', color: 'rgba(255,255,255,0.6)', marginLeft: '4px', zIndex: 10 }} 
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteAlert(alert.id);
                }}
              />
            </div>
          ))}
        </div>
      )}

      {/* Alert Modal */}
      {isAlertModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          backdropFilter: 'blur(10px)'
        }}>
          <div style={{
            background: '#0d1b2a',
            border: '1px solid var(--border)',
            borderRadius: '20px',
            padding: '2rem',
            width: '100%',
            maxWidth: '450px',
            boxShadow: '0 20px 50px rgba(0,0,0,0.5)'
          }}>
            <h2 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Bell size={24} color="var(--primary)" />
              Create AI Alert
            </h2>
            
            <form onSubmit={handleCreateAlert}>
              <div style={{ marginBottom: '1.2rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '8px' }}>Select Asset</label>
                <select 
                  value={alertForm.coin_id}
                  onChange={(e) => setAlertForm({ ...alertForm, coin_id: e.target.value })}
                  style={{ width: '100%' }}
                >
                  {marketData.map(coin => (
                    <option key={coin.coin_id} value={coin.coin_id}>
                      {coin.name} ({coin.symbol.toUpperCase()})
                    </option>
                  ))}
                </select>
              </div>
              
              <div style={{ marginBottom: '1.2rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '8px' }}>Alert Type</label>
                <select 
                  value={alertForm.alert_type}
                  onChange={(e) => setAlertForm({ ...alertForm, alert_type: e.target.value })}
                  style={{ width: '100%' }}
                >
                  <option value="price_above">Price goes above</option>
                  <option value="price_below">Price goes below</option>
                </select>
              </div>
              
              <div style={{ marginBottom: '2rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '8px' }}>Price Threshold (USD)</label>
                <input 
                  type="number" 
                  step="any"
                  placeholder="e.g. 75000"
                  value={alertForm.threshold}
                  onChange={(e) => setAlertForm({ ...alertForm, threshold: e.target.value })}
                  required
                  style={{ width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '8px', padding: '0.8rem', color: 'white' }}
                />
              </div>
              
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button 
                  type="button"
                  onClick={() => setIsAlertModalOpen(false)}
                  style={{ flex: 1, padding: '0.8rem', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '10px', color: 'white', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={isSubmitting}
                  style={{ flex: 1, padding: '0.8rem', background: 'linear-gradient(90deg, var(--primary), var(--secondary))', border: 'none', borderRadius: '10px', color: 'black', fontWeight: 700, cursor: 'pointer' }}
                >
                  {isSubmitting ? 'Creating...' : 'Set AI Alert'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Filters & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', gap: '1.5rem', flexWrap: 'wrap' }}>
        <div className="category-scroll-container" style={{ display: 'flex', gap: '0.8rem', overflowX: 'auto', flex: 1, paddingBottom: '4px', scrollbarWidth: 'none' }}>
          {categories.map(cat => (
            <button 
              key={cat} 
              className={`category-pill ${category === cat ? 'active' : ''}`}
              onClick={() => setCategory(cat)}
              style={{ fontWeight: 600, fontSize: '0.8rem' }}
            >
              {cat}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div style={{ position: 'relative' }}>
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
            <input 
              type="text" 
              placeholder="Search assets..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ 
                paddingLeft: '42px', 
                width: '260px', 
                background: 'rgba(13, 27, 42, 0.4)',
                borderRadius: '10px',
                fontSize: '0.9rem'
              }}
            />
          </div>
          
          <div style={{ display: 'flex', background: 'rgba(255,255,255,0.05)', borderRadius: '10px', padding: '4px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <button 
              onClick={() => setViewMode('list')} 
              style={{ 
                padding: '8px 12px', 
                background: viewMode === 'list' ? 'rgba(255,255,255,0.1)' : 'transparent',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                color: viewMode === 'list' ? 'white' : 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <ListIcon size={20} />
            </button>
            <button 
              onClick={() => setViewMode('heatmap')} 
              style={{ 
                padding: '8px 12px', 
                background: viewMode === 'heatmap' ? 'rgba(255,255,255,0.1)' : 'transparent',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                color: viewMode === 'heatmap' ? 'white' : 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <Grid3X3 size={20} />
            </button>
          </div>
        </div>
      </div>

      {viewMode === 'list' ? (
        <div className="market-table-container">
          <table className="market-table">
            <thead>
              <tr>
                <th style={{ width: '40px' }}></th>
                <th style={{ width: '50px', textAlign: 'center' }}>#</th>
                <th style={{ width: '220px' }}>Name</th>
                <th style={{ textAlign: 'right' }}>Price</th>
                <th style={{ textAlign: 'right' }}>1h %</th>
                <th style={{ textAlign: 'right' }}>24h %</th>
                <th style={{ textAlign: 'right' }}>7d %</th>
                <th style={{ textAlign: 'right' }}>Market Cap</th>
                <th style={{ textAlign: 'right' }}>Volume(24h)</th>
                <th style={{ width: '200px' }}>Circulating Supply</th>
                <th style={{ width: '120px' }}>Last 7 Days</th>
              </tr>
            </thead>
            <tbody>
              {filteredData.map((coin, i) => (
                <tr key={coin.coin_id}>
                  <td>
                    <button 
                      onClick={() => toggleWatchlist(coin.coin_id)}
                      className="watchlist-btn"
                    >
                      <Star 
                        size={16} 
                        fill={watchlist.includes(coin.coin_id) ? 'var(--primary)' : 'none'} 
                        color={watchlist.includes(coin.coin_id) ? 'var(--primary)' : 'var(--text-muted)'} 
                      />
                    </button>
                  </td>
                  <td style={{ color: 'var(--text-muted)', textAlign: 'center', fontSize: '0.8rem' }}>{coin.market_cap_rank || i + 1}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <img src={coin.image} alt="" style={{ width: 28, height: 28, borderRadius: '50%' }} />
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                        <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>{coin.name}</span>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600 }}>{coin.symbol?.toUpperCase()}</span>
                      </div>
                    </div>
                  </td>
                  <td style={{ fontWeight: 700, textAlign: 'right', color: 'var(--text-main)' }}>
                    ${coin.price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className={coin.change_1h >= 0 ? 'positive' : 'negative'} style={{ textAlign: 'right', fontWeight: 600 }}>
                    {coin.change_1h ? `${coin.change_1h.toFixed(2)}%` : '0.00%'}
                  </td>
                  <td className={coin.change_24h >= 0 ? 'positive' : 'negative'} style={{ textAlign: 'right', fontWeight: 600 }}>
                    {coin.change_24h ? `${coin.change_24h.toFixed(2)}%` : '0.00%'}
                  </td>
                  <td className={coin.change_7d >= 0 ? 'positive' : 'negative'} style={{ textAlign: 'right', fontWeight: 600 }}>
                    {coin.change_7d ? `${coin.change_7d.toFixed(2)}%` : '0.00%'}
                  </td>
                  <td style={{ textAlign: 'right', fontWeight: 500 }}>{formatLargeNumber(coin.market_cap)}</td>
                  <td style={{ textAlign: 'right', fontWeight: 500 }}>{formatLargeNumber(coin.total_volume)}</td>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                        {coin.circulating_supply?.toLocaleString(undefined, { maximumFractionDigits: 0 })} <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>{coin.symbol?.toUpperCase()}</span>
                      </div>
                      <div className="supply-bar">
                        <div className="supply-bar-fill" style={{ width: coin.max_supply ? `${(coin.circulating_supply / coin.max_supply) * 100}%` : '45%' }}></div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <Sparkline data={coin.sparkline_7d} color={coin.change_7d >= 0 ? '#00e676' : '#ff1744'} />
                  </td>
                </tr>
              ))}
              {filteredData.length === 0 && (
                <tr>
                  <td colSpan="11" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                    No assets found in this category.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <MarketHeatmap data={filteredData} />
      )}

      {/* AI Chat History Container */}
      {isChatOpen && (
        <div className="ai-chat-container">
          <div className="chat-messages">
            {chatHistory.map((msg, i) => (
              <div key={i} className={`chat-message ${msg.type}`}>
                {msg.text}
              </div>
            ))}
            {isChatLoading && (
              <div className="chat-message ai">
                <div className="chat-loading">
                  <div className="dot"></div>
                  <div className="dot"></div>
                  <div className="dot"></div>
                </div>
              </div>
            )}
          </div>
          {/* Quick Suggestions */}
          <div style={{ padding: '0 1rem 1rem', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {['Market Sentiment', 'Top Movers', 'Portfolio Risk'].map(hint => (
              <button 
                key={hint}
                className="category-pill"
                style={{ fontSize: '0.75rem', padding: '4px 12px' }}
                onClick={() => {
                  handleChatSubmit(null, hint)
                }}
              >
                {hint}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* AI Chat Bar */}
      <div style={{ 
        position: 'fixed', 
        bottom: '2.5rem', 
        left: '50%', 
        transform: 'translateX(-50%)',
        zIndex: 100,
        width: '100%',
        padding: '0 2rem',
        display: 'flex',
        justifyContent: 'center'
      }}>
        <div className="ai-chat-bar">
          <MessageSquare 
            size={20} 
            color={isChatOpen ? 'var(--primary)' : 'var(--text-muted)'} 
            style={{ cursor: 'pointer' }}
            onClick={() => setIsChatOpen(!isChatOpen)}
          />
          <input 
            type="text" 
            placeholder="Ask AI about the market..." 
            className="ai-chat-input"
            value={chatMessage}
            onChange={(e) => setChatMessage(e.target.value)}
            onKeyDown={handleChatSubmit}
            onFocus={() => setIsChatOpen(true)}
          />
          <div className="shortcut-badge">Enter</div>
        </div>
      </div>
    </div>
  )
}
