import { useState, useEffect, useMemo } from 'react'
import { io } from 'socket.io-client'
import { apiFetch, API_BASE } from '../lib/api.js'
import { TrendingUp, TrendingDown, Wallet, Zap, BarChart3, PieChart as PieIcon, FileText, Download } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function Dashboard() {
  const [marketData, setMarketData] = useState([])
  const [loading, setLoading] = useState(true)
  const [portfolio, setPortfolio] = useState(null)
  const [btcHistory, setBtcHistory] = useState([])
  const [livePrices, setLivePrices] = useState({})
  const [isGeneratingReport, setIsGeneratingReport] = useState(false)
  const [lastReport, setLastReport] = useState(null)

  useEffect(() => {
    const fetchMarket = async () => {
      try {
        const res = await apiFetch('/api/market?per_page=10')
        setMarketData(res.data || [])
      } catch (err) {
        console.error('Error fetching market data:', err)
      }
    }

    const fetchPortfolio = async () => {
      try {
        const res = await apiFetch('/api/portfolios', { auth: true })
        if (res.data && res.data.length > 0) {
          setPortfolio(res.data[0])
        }
      } catch (err) {
        console.error('Error fetching portfolio:', err)
      }
    }

    const fetchHistory = async () => {
      try {
        const res = await apiFetch('/api/market/bitcoin/history?days=7')
        setBtcHistory(res.data || [])
      } catch (err) {
        console.error('Error fetching history:', err)
      }
    }

    const fetchData = async () => {
      setLoading(true)
      await Promise.allSettled([
        fetchMarket(),
        fetchPortfolio(),
        fetchHistory()
      ])
      setLoading(false)
    }
    
    fetchData()

    // Live updates
    const socket = io(API_BASE.replace('/api', ''))
    socket.on('market_update', (newData) => {
      const priceMap = {}
      newData.forEach(coin => {
        priceMap[coin.coin_id || coin.id] = coin.price || coin.current_price
      })
      setLivePrices(prev => ({ ...prev, ...priceMap }))
    })

    return () => socket.disconnect()
  }, [])

  const handleGenerateReport = async (type = 'portfolio') => {
    setIsGeneratingReport(true)
    try {
      const endpoint = type === 'portfolio' 
        ? `/api/report/portfolio/${portfolio.id}` 
        : '/api/report/market'
      const res = await apiFetch(endpoint, { auth: true })
      setLastReport(res.data)
      alert('Report generated successfully!')
    } catch (err) {
      console.error('Report error:', err)
      alert('Failed to generate report: ' + err.message)
    } finally {
      setIsGeneratingReport(false)
    }
  }

  const stats = useMemo(() => {
    if (!portfolio) return { totalValue: 0, totalPl: 0, totalPlPct: 0 }
    
    let currentTotal = 0
    let costBasisTotal = 0
    
    portfolio.assets?.forEach(asset => {
      const currentPrice = livePrices[asset.coin_id] || asset.current_price
      currentTotal += asset.quantity * currentPrice
      costBasisTotal += asset.quantity * asset.purchase_price
    })
    
    const totalPl = currentTotal - costBasisTotal
    const totalPlPct = costBasisTotal > 0 ? (totalPl / costBasisTotal * 100) : 0
    
    return {
      totalValue: currentTotal,
      totalPl,
      totalPlPct
    }
  }, [portfolio, livePrices])

  const topPerformer = useMemo(() => {
    if (marketData.length === 0) return null
    return [...marketData].sort((a, b) => (b.change_24h || 0) - (a.change_24h || 0))[0]
  }, [marketData])

  const chartData = useMemo(() => {
    return btcHistory.map(item => ({
      name: new Date(item.timestamp).toLocaleDateString(undefined, { weekday: 'short' }),
      value: item.price
    }))
  }, [btcHistory])

  if (loading) return (
    <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
      <div className="loader">Analyzing Market...</div>
    </div>
  )

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '4rem' }}>
      <header style={{ marginBottom: '2.5rem' }}>
        <h1 style={{ fontSize: '2.4rem', fontWeight: 800, marginBottom: '0.4rem' }}>Market Overview</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>Real-time intelligence for your crypto portfolio.</p>
      </header>

      {(!portfolio || portfolio.assets?.length === 0) && (
        <div className="card" style={{ 
          marginBottom: '2.5rem', 
          background: 'linear-gradient(90deg, rgba(0, 212, 255, 0.1), rgba(123, 47, 239, 0.1))',
          border: '1px solid rgba(0, 212, 255, 0.2)',
          padding: '2rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1.5rem'
        }}>
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>Ready to start tracking?</h2>
            <p style={{ color: 'var(--text-muted)' }}>Your dashboard is currently empty. Add your first asset to see your portfolio performance here.</p>
          </div>
          <button 
            className="btn" 
            onClick={() => window.location.href = '/portfolio'}
            style={{ padding: '0.8rem 2rem', borderRadius: '12px' }}
          >
            Go to Portfolio
          </button>
        </div>
      )}

      <div className="stat-grid" style={{ marginBottom: '2.5rem' }}>
        <div className="stat-card" style={{ padding: '1.8rem', borderRadius: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.2rem' }}>
            <span className="stat-label" style={{ fontWeight: 600, fontSize: '0.85rem' }}>TOTAL BALANCE</span>
            <Wallet size={20} color="var(--primary)" />
          </div>
          <div className="stat-value" style={{ fontSize: '2.2rem', fontWeight: 800 }}>${stats.totalValue.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
          <div style={{ marginTop: '0.6rem', fontSize: '0.95rem', fontWeight: 600 }} className={stats.totalPl >= 0 ? 'positive' : 'negative'}>
            {stats.totalPl >= 0 ? '+' : '-'}${Math.abs(stats.totalPl).toLocaleString(undefined, { minimumFractionDigits: 2 })} ({stats.totalPlPct.toFixed(2)}%)
          </div>
        </div>

        <div className="stat-card" style={{ padding: '1.8rem', borderRadius: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.2rem' }}>
            <span className="stat-label" style={{ fontWeight: 600, fontSize: '0.85rem' }}>TOP PERFORMER</span>
            <Zap size={20} color="#FFD700" />
          </div>
          <div className="stat-value" style={{ fontSize: '2.2rem', fontWeight: 800 }}>{topPerformer?.symbol?.toUpperCase() || 'N/A'}</div>
          <div style={{ marginTop: '0.6rem', fontSize: '0.95rem', fontWeight: 600 }} className={(topPerformer?.change_24h || 0) >= 0 ? 'positive' : 'negative'}>
            {(topPerformer?.change_24h || 0) >= 0 ? '+' : ''}{(topPerformer?.change_24h || 0).toFixed(2)}% (24h)
          </div>
        </div>

        <div className="stat-card" style={{ padding: '1.8rem', borderRadius: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.2rem' }}>
            <span className="stat-label" style={{ fontWeight: 600, fontSize: '0.85rem' }}>ACTIVE ASSETS</span>
            <PieIcon size={20} color="var(--secondary)" />
          </div>
          <div className="stat-value" style={{ fontSize: '2.2rem', fontWeight: 800 }}>{portfolio?.num_assets || 0}</div>
          <div style={{ marginTop: '0.6rem', fontSize: '0.95rem', color: 'var(--text-muted)', fontWeight: 600 }}>
            Across {portfolio?.name || 'Portfolio'}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
        <div className="card" style={{ padding: '2rem', borderRadius: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
            <h3 style={{ fontSize: '1.3rem', fontWeight: 700 }}>Market Trend (Bitcoin)</h3>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600 }}>LAST 7 DAYS</div>
          </div>
          <div style={{ height: '320px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} axisLine={false} tickLine={false} />
                <YAxis hide domain={['auto', 'auto']} />
                <Tooltip 
                  contentStyle={{ background: '#0d1b2a', border: '1px solid var(--border)', borderRadius: '12px', boxShadow: '0 10px 30px rgba(0,0,0,0.3)' }}
                  itemStyle={{ color: 'white', fontWeight: 600 }}
                  labelStyle={{ color: 'var(--text-muted)', marginBottom: '4px' }}
                />
                <Area type="monotone" dataKey="value" stroke="var(--primary)" strokeWidth={3} fillOpacity={1} fill="url(#colorValue)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card" style={{ padding: '2rem', borderRadius: '24px' }}>
          <h3 style={{ marginBottom: '1.8rem', fontSize: '1.3rem', fontWeight: 700 }}>Top Movers</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
            {marketData.slice(0, 5).map(coin => (
              <div key={coin.coin_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.8rem 1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ fontWeight: 800, color: 'var(--primary)', fontSize: '0.8rem' }}>{coin.symbol.toUpperCase()}</div>
                  <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{coin.name}</span>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 700 }}>${(livePrices[coin.coin_id] || coin.price).toLocaleString()}</div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600 }} className={coin.change_24h >= 0 ? 'positive' : 'negative'}>
                    {coin.change_24h >= 0 ? '+' : ''}{coin.change_24h.toFixed(2)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Reports Section */}
      <div className="card" style={{ marginTop: '2.5rem', padding: '2.5rem', borderRadius: '24px', background: 'rgba(123, 47, 239, 0.03)', border: '1px solid rgba(123, 47, 239, 0.1)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '2rem' }}>
          <div>
            <h3 style={{ fontSize: '1.6rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '0.4rem' }}>
              <FileText size={28} color="var(--secondary)" />
              Smart Analysis Reports
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>Generate detailed PDF/CSV summaries of your performance and market conditions.</p>
          </div>
          
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button 
              onClick={() => handleGenerateReport('market')}
              disabled={isGeneratingReport}
              className="btn btn-secondary"
              style={{ padding: '0.8rem 1.8rem', borderRadius: '12px' }}
            >
              Market Overview
            </button>
            <button 
              onClick={() => handleGenerateReport('portfolio')}
              disabled={isGeneratingReport || !portfolio}
              className="btn btn-primary"
              style={{ padding: '0.8rem 1.8rem', borderRadius: '12px', color: 'black', fontWeight: 700 }}
            >
              {isGeneratingReport ? 'Generating...' : 'Portfolio Deep-Dive'}
            </button>
          </div>
        </div>

        {lastReport && (
          <div style={{ marginTop: '2.5rem', padding: '1.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '16px', border: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
              <div style={{ width: 45, height: 45, borderRadius: '12px', background: 'rgba(0, 230, 118, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Download size={24} color="var(--positive)" />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1rem' }}>Report Ready: {lastReport.csv_path.split(/[\\/]/).pop()}</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Generated at {new Date(lastReport.generated_at).toLocaleString()}</div>
              </div>
            </div>
            <a 
              href={`${API_BASE.replace('/api', '')}/reports/${lastReport.csv_path.split(/[\\/]/).pop()}`} 
              target="_blank" 
              rel="noreferrer"
              className="btn"
              style={{ padding: '0.6rem 1.2rem', fontSize: '0.9rem', borderRadius: '10px' }}
            >
              Download CSV
            </a>
          </div>
        )}
      </div>
    </div>
  )
}
