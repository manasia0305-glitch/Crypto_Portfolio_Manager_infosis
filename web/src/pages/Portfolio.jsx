import { useState, useEffect, useMemo } from 'react'
import { io } from 'socket.io-client'
import { apiFetch, API_BASE } from '../lib/api.js'
import { Wallet, Plus, Trash2, PieChart, TrendingUp, TrendingDown, X, DollarSign, Activity, PieChart as PieIcon, Briefcase, ShieldCheck } from 'lucide-react'
import { PieChart as RePieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

export default function Portfolio() {
  const [portfolios, setPortfolios] = useState([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [newHolding, setNewHolding] = useState({ coin_id: 'bitcoin', quantity: '', purchase_price: '' })
  const [livePrices, setLivePrices] = useState({})
  const [optimizationResult, setOptimizationResult] = useState(null)
  const [isOptimizing, setIsOptimizing] = useState(false)

  useEffect(() => {
    const fetchPortfolios = async () => {
      try {
        const data = await apiFetch('/api/portfolios', { auth: true })
        setPortfolios(data.data || [])
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchPortfolios()

    // Real-time market updates via Socket.io
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

  const currentPortfolio = useMemo(() => {
    if (portfolios.length === 0) return null
    const p = { ...portfolios[0] }
    
    // Update assets with live prices and recalculate P&L
    let totalValue = 0
    let totalCost = 0
    
    if (p.assets) {
      p.assets = p.assets.map(asset => {
        const currentPrice = livePrices[asset.coin_id] || asset.current_price
        const currentValue = asset.quantity * currentPrice
        const costBasis = asset.quantity * asset.purchase_price
        const profitLoss = currentValue - costBasis
        const profitLossPct = costBasis > 0 ? (profitLoss / costBasis * 100) : 0
        
        totalValue += currentValue
        totalCost += costBasis
        
        return {
          ...asset,
          current_price: currentPrice,
          current_value: currentValue,
          profit_loss: profitLoss,
          profit_loss_pct: profitLossPct
        }
      })
    }
    
    p.total_value = totalValue
    p.total_pl = totalValue - totalCost
    p.total_pl_pct = totalCost > 0 ? (p.total_pl / totalCost * 100) : 0
    
    return p
  }, [portfolios, livePrices])

  const COLORS = ['#00d4ff', '#7b2fef', '#ff0080', '#00e676', '#ff1744']

  const allocationData = useMemo(() => 
    currentPortfolio?.assets?.map(asset => ({
      name: asset.name,
      value: asset.current_value
    })) || [], [currentPortfolio])

  const handleAddHolding = async (e) => {
    e.preventDefault()
    setIsSubmitting(true)
    
    const holdingData = {
      coin_id: newHolding.coin_id.toLowerCase().trim(),
      quantity: parseFloat(newHolding.quantity),
      purchase_price: parseFloat(newHolding.purchase_price)
    }

    if (isNaN(holdingData.quantity) || isNaN(holdingData.purchase_price)) {
      alert('Please enter valid numeric values.')
      setIsSubmitting(false)
      return
    }

    try {
      let targetPortfolioId = currentPortfolio?.id
      if (!targetPortfolioId) {
        const pData = await apiFetch('/api/portfolio', { method: 'POST', body: { name: 'My Portfolio' }, auth: true })
        targetPortfolioId = pData.portfolio_id
      }

      await apiFetch(`/api/portfolio/${targetPortfolioId}/holding`, { method: 'POST', body: holdingData, auth: true })
      
      const data = await apiFetch('/api/portfolios', { auth: true })
      setPortfolios(data.data || [])
      setIsModalOpen(false)
      setNewHolding({ coin_id: 'bitcoin', quantity: '', purchase_price: '' })
    } catch (err) {
      console.error('Error adding holding:', err)
      if (err.status === 401) {
        alert('Your session is invalid or has expired. Please log in again.')
        localStorage.removeItem('token')
        window.location.href = '/login'
      } else {
        alert('Error: ' + err.message)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDeleteAsset = async (coinId) => {
    if (!window.confirm(`Are you sure you want to remove all holdings of ${coinId}?`)) return
    
    try {
      await apiFetch(`/api/portfolio/${currentPortfolio.id}/holding/${coinId}`, {
        method: 'DELETE',
        auth: true
      })
      // Refresh portfolios
      const data = await apiFetch('/api/portfolios', { auth: true })
      setPortfolios(data.data || [])
    } catch (err) {
      console.error('Error deleting asset:', err)
      alert('Failed to delete asset: ' + err.message)
    }
  }

  const handleOptimize = async (type = 'standard') => {
    setIsOptimizing(true)
    try {
      const endpoint = type === 'monte-carlo' ? '/api/optimize/monte-carlo' : '/api/optimize?objective=max_sharpe'
      const data = await apiFetch(endpoint, { auth: true })
      setOptimizationResult(data.data)
    } catch (err) {
      console.error('Optimization error:', err)
      alert('Optimization failed: ' + err.message)
    } finally {
      setIsOptimizing(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-dark)' }}>
      <div className="loader">Loading your assets...</div>
    </div>
  )

  return (
    <div style={{ paddingBottom: '4rem', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ 
        marginBottom: '2.5rem', 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        padding: '0 0.5rem'
      }}>
        <div>
          <h1 style={{ fontSize: '2.4rem', fontWeight: 800, marginBottom: '0.4rem', letterSpacing: '-0.02em' }}>Portfolio Manager</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>Manage your assets and track performance.</p>
        </div>
        
        <button 
          onClick={() => setIsModalOpen(true)} 
          className="btn"
          style={{ 
            padding: '0.75rem 1.8rem', 
            borderRadius: '12px', 
            fontSize: '1rem',
            fontWeight: 700,
            background: 'linear-gradient(90deg, var(--primary), var(--secondary))',
            color: 'black',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            boxShadow: '0 4px 15px rgba(0, 212, 255, 0.2)'
          }}
        >
          <Plus size={20} /> Add Holding
        </button>
      </header>

      {!currentPortfolio || currentPortfolio.assets.length === 0 ? (
        <div className="card" style={{ 
          textAlign: 'center', 
          padding: '6rem 2rem', 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          justifyContent: 'center',
          background: 'rgba(13, 27, 42, 0.4)',
          border: '1px dashed rgba(255, 255, 255, 0.1)',
          borderRadius: '24px',
          minHeight: '450px'
        }}>
          <div style={{ 
            background: 'rgba(0, 212, 255, 0.1)', 
            padding: '2rem', 
            borderRadius: '50%', 
            marginBottom: '2rem',
            color: 'var(--primary)'
          }}>
            <Wallet size={64} />
          </div>
          <h2 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '1rem' }}>No portfolios found</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '3rem', maxWidth: '420px', fontSize: '1.1rem', lineHeight: 1.6 }}>
            Your crypto journey starts here. Create your first portfolio to start tracking your investments.
          </p>
          <button 
            className="btn" 
            style={{ 
              padding: '1rem 3rem', 
              borderRadius: '14px', 
              fontWeight: 800, 
              color: 'black',
              fontSize: '1.1rem'
            }}
            onClick={async () => {
              try {
                setLoading(true)
                await apiFetch('/api/portfolio/sample', { method: 'POST', auth: true })
                const data = await apiFetch('/api/portfolios', { auth: true })
                setPortfolios(data.data || [])
                alert('Demo portfolio created successfully!')
              } catch (err) {
                console.error(err)
              } finally {
                setLoading(false)
              }
            }}
          >
            Create Demo Portfolio
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '2rem' }}>
          {/* Summary Cards */}
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
            gap: '1.5rem' 
          }}>
            <div className="card" style={{ padding: '2rem', borderRadius: '20px', background: 'rgba(13, 27, 42, 0.6)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 600 }}>TOTAL VALUE</span>
                <Briefcase size={20} color="var(--primary)" />
              </div>
              <div style={{ fontSize: '2.4rem', fontWeight: 800 }}>${currentPortfolio.total_value?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
            </div>

            <div className="card" style={{ padding: '2rem', borderRadius: '20px', background: 'rgba(13, 27, 42, 0.6)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 600 }}>TOTAL P&L</span>
                <Activity size={20} color={currentPortfolio.total_pl >= 0 ? 'var(--positive)' : 'var(--negative)'} />
              </div>
              <div style={{ 
                fontSize: '2.4rem', 
                fontWeight: 800,
                color: currentPortfolio.total_pl >= 0 ? 'var(--positive)' : 'var(--negative)'
              }}>
                {currentPortfolio.total_pl >= 0 ? '+' : '-'}${Math.abs(currentPortfolio.total_pl || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </div>
              <div style={{ marginTop: '0.5rem', fontWeight: 600, color: currentPortfolio.total_pl >= 0 ? 'var(--positive)' : 'var(--negative)' }}>
                {currentPortfolio.total_pl_pct?.toFixed(2)}% overall
              </div>
            </div>

            <div className="card" style={{ padding: '2rem', borderRadius: '20px', background: 'rgba(13, 27, 42, 0.6)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 600 }}>ACTIVE ASSETS</span>
                <PieIcon size={20} color="var(--secondary)" />
              </div>
              <div style={{ fontSize: '2.4rem', fontWeight: 800 }}>{currentPortfolio.num_assets}</div>
              <div style={{ marginTop: '0.5rem', color: 'var(--text-muted)', fontWeight: 500 }}>Diversified across markets</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem', flexWrap: 'wrap' }} className="portfolio-layout">
            {/* Holdings Table */}
            <div className="card" style={{ padding: '0', borderRadius: '24px', overflow: 'hidden' }}>
              <div style={{ padding: '1.5rem 2rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontSize: '1.3rem', fontWeight: 700 }}>Your Holdings</h3>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table className="market-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ textAlign: 'left', background: 'rgba(255,255,255,0.02)' }}>
                      <th style={{ padding: '1.2rem 2rem' }}>Asset</th>
                      <th style={{ padding: '1.2rem 1.5rem' }}>Balance</th>
                      <th style={{ padding: '1.2rem 1.5rem' }}>Avg Price</th>
                      <th style={{ padding: '1.2rem 1.5rem' }}>Current</th>
                      <th style={{ padding: '1.2rem 2rem', textAlign: 'right' }}>Profit/Loss</th>
                      <th style={{ padding: '1.2rem 2rem', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentPortfolio.assets?.map((asset, idx) => (
                      <tr key={`${asset.coin_id}-${idx}`} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '1.2rem 2rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '8px', borderRadius: '10px' }}>
                              <span style={{ fontWeight: 800, fontSize: '0.8rem', color: 'var(--primary)' }}>{asset.symbol?.toUpperCase()}</span>
                            </div>
                            <div>
                              <div style={{ fontWeight: 700, fontSize: '1rem' }}>{asset.name}</div>
                              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{asset.coin_id}</div>
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: '1.2rem 1.5rem' }}>
                          <div style={{ fontWeight: 600 }}>{(asset.quantity || 0).toLocaleString()}</div>
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>${(asset.current_value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                        </td>
                        <td style={{ padding: '1.2rem 1.5rem', color: 'var(--text-muted)' }}>${(asset.purchase_price || 0).toLocaleString()}</td>
                        <td style={{ padding: '1.2rem 1.5rem', fontWeight: 600 }}>${(asset.current_price || 0).toLocaleString()}</td>
                        <td style={{ padding: '1.2rem 2rem', textAlign: 'right' }}>
                          <div style={{ fontWeight: 700 }} className={asset.profit_loss >= 0 ? 'positive' : 'negative'}>
                            {asset.profit_loss >= 0 ? '+' : '-'}${Math.abs(asset.profit_loss || 0).toLocaleString()}
                          </div>
                          <div style={{ fontSize: '0.8rem', fontWeight: 600 }} className={asset.profit_loss >= 0 ? 'positive' : 'negative'}>
                            {(asset.profit_loss_pct || 0).toFixed(2)}%
                          </div>
                        </td>
                        <td style={{ padding: '1.2rem 2rem', textAlign: 'right' }}>
                          <button 
                            onClick={() => handleDeleteAsset(asset.coin_id)}
                            style={{ 
                              background: 'rgba(255, 23, 68, 0.1)', 
                              border: 'none', 
                              color: 'var(--danger)', 
                              padding: '8px', 
                              borderRadius: '8px', 
                              cursor: 'pointer',
                              transition: 'all 0.2s'
                            }}
                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255, 23, 68, 0.2)'}
                            onMouseLeave={e => e.currentTarget.style.background = 'rgba(255, 23, 68, 0.1)'}
                            title="Remove Asset"
                          >
                            <Trash2 size={18} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Allocation Chart */}
            <div className="card" style={{ borderRadius: '24px', padding: '2rem' }}>
              <h3 style={{ marginBottom: '2rem', fontSize: '1.3rem', fontWeight: 700 }}>Asset Allocation</h3>
              <div style={{ height: '300px', position: 'relative' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RePieChart>
                    <Pie
                      data={allocationData}
                      cx="50%"
                      cy="50%"
                      innerRadius={80}
                      outerRadius={110}
                      paddingAngle={8}
                      dataKey="value"
                      stroke="none"
                    >
                      {allocationData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ background: '#0d1b2a', border: '1px solid var(--border)', borderRadius: '12px', boxShadow: '0 10px 30px rgba(0,0,0,0.3)' }}
                      itemStyle={{ color: 'white', fontWeight: 600 }}
                    />
                  </RePieChart>
                </ResponsiveContainer>
                <div style={{ 
                  position: 'absolute', 
                  top: '50%', 
                  left: '50%', 
                  transform: 'translate(-50%, -50%)',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>DIVERSITY</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>{currentPortfolio.num_assets}</div>
                </div>
              </div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '2.5rem' }}>
                {allocationData.map((asset, index) => (
                  <div key={asset.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div style={{ width: 14, height: 14, borderRadius: '4px', background: COLORS[index % COLORS.length] }} />
                      <span style={{ fontSize: '0.95rem', fontWeight: 600 }}>{asset.name}</span>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>${asset.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                        {((asset.value / currentPortfolio.total_value) * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Optimization Section */}
            <div className="card" style={{ gridColumn: '1 / -1', padding: '2.5rem', borderRadius: '24px', background: 'rgba(0, 212, 255, 0.03)', border: '1px solid rgba(0, 212, 255, 0.1)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
                <div>
                  <h3 style={{ fontSize: '1.6rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '0.4rem' }}>
                    <ShieldCheck size={28} color="var(--primary)" />
                    AI Portfolio Optimization
                  </h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>Rebalance your assets for maximum returns and minimum risk using MPT models.</p>
                </div>
                <div style={{ display: 'flex', gap: '1rem' }}>
                  <button 
                    onClick={() => handleOptimize('standard')}
                    disabled={isOptimizing}
                    className="btn btn-secondary"
                    style={{ padding: '0.7rem 1.5rem', borderRadius: '12px' }}
                  >
                    {isOptimizing ? 'Running...' : 'Optimize (MPT)'}
                  </button>
                  <button 
                    onClick={() => handleOptimize('monte-carlo')}
                    disabled={isOptimizing}
                    className="btn btn-primary"
                    style={{ padding: '0.7rem 1.5rem', borderRadius: '12px', color: 'black', fontWeight: 700 }}
                  >
                    {isOptimizing ? 'Simulating...' : 'Monte Carlo (10k)'}
                  </button>
                </div>
              </div>

              {optimizationResult ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2.5rem' }}>
                  <div style={{ background: 'rgba(255,255,255,0.02)', padding: '2rem', borderRadius: '20px', border: '1px solid var(--border)' }}>
                    <h4 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.5rem', color: 'var(--primary)' }}>TARGET ALLOCATIONS</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
                      {(() => {
                        const weights = optimizationResult.max_sharpe_portfolio?.weights;
                        const allocations = optimizationResult.allocations;
                        
                        // Convert object weights to array if needed
                        const displayAllocations = allocations || (weights ? Object.entries(weights).map(([asset, weight]) => ({
                          asset,
                          weight_pct: weight * 100
                        })) : []);

                        return displayAllocations.map((alloc, i) => {
                          const name = alloc.asset || i;
                          const weight = alloc.weight_pct;
                          
                          return (
                            <div key={name}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.9rem' }}>
                                <span style={{ fontWeight: 600 }}>{name.toString().toUpperCase()}</span>
                                <span style={{ fontWeight: 800, color: 'var(--primary)' }}>{weight.toFixed(1)}%</span>
                              </div>
                              <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                                <div style={{ width: `${Math.min(100, Math.max(0, weight))}%`, height: '100%', background: 'var(--primary)', boxShadow: '0 0 10px var(--primary)' }} />
                              </div>
                            </div>
                          );
                        });
                      })()}
                    </div>
                  </div>

                  <div style={{ background: 'rgba(255,255,255,0.02)', padding: '2rem', borderRadius: '20px', border: '1px solid var(--border)' }}>
                    <h4 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.5rem', color: 'var(--secondary)' }}>PROJECTED PERFORMANCE</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '4px' }}>EXPECTED ANNUAL RETURN</div>
                          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--positive)' }}>
                            +{( (optimizationResult.max_sharpe_portfolio?.expected_return || optimizationResult.expected_annual_return || 0) * 100).toFixed(1)}%
                          </div>
                        </div>
                        <TrendingUp size={32} color="var(--positive)" style={{ opacity: 0.3 }} />
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '4px' }}>ANNUAL VOLATILITY</div>
                          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--warning)' }}>
                            {( (optimizationResult.max_sharpe_portfolio?.volatility || optimizationResult.annual_volatility || 0) * 100).toFixed(1)}%
                          </div>
                        </div>
                        <Activity size={32} color="var(--warning)" style={{ opacity: 0.3 }} />
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '4px' }}>SHARPE RATIO</div>
                          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--secondary)' }}>
                            {(optimizationResult.max_sharpe_portfolio?.sharpe_ratio || optimizationResult.sharpe_ratio || 0).toFixed(2)}
                          </div>
                        </div>
                        <ShieldCheck size={32} color="var(--secondary)" style={{ opacity: 0.3 }} />
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.02)', borderRadius: '16px' }}>
                  Click one of the optimization buttons above to see your ideal asset allocation.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Add Holding Modal */}
      {isModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.85)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          backdropFilter: 'blur(12px)',
          padding: '1rem'
        }}>
          <div style={{
            background: '#0d1b2a',
            border: '1px solid var(--border)',
            borderRadius: '28px',
            padding: '2.5rem',
            width: '100%',
            maxWidth: '500px',
            boxShadow: '0 25px 60px rgba(0,0,0,0.6)',
            position: 'relative'
          }}>
            <button 
              onClick={() => setIsModalOpen(false)}
              style={{ position: 'absolute', top: '1.5rem', right: '1.5rem', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
            >
              <X size={24} />
            </button>

            <h2 style={{ marginBottom: '2rem', fontSize: '1.8rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ background: 'var(--primary)', padding: '8px', borderRadius: '12px', color: 'black' }}>
                <Plus size={24} />
              </div>
              Add New Asset
            </h2>
            
            <form onSubmit={handleAddHolding} style={{ display: 'grid', gap: '1.5rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '10px', fontWeight: 600 }}>Asset (Coin ID)</label>
                <div style={{ position: 'relative' }}>
                  <Briefcase size={18} color="var(--text-muted)" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
                  <input 
                    type="text" 
                    placeholder="e.g. bitcoin, ethereum, solana" 
                    value={newHolding.coin_id} 
                    onChange={e => setNewHolding({ ...newHolding, coin_id: e.target.value })} 
                    required 
                    style={{ paddingLeft: '44px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)', borderRadius: '14px', padding: '1rem 1rem 1rem 2.8rem' }}
                  />
                </div>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '10px', fontWeight: 600 }}>Quantity</label>
                  <div style={{ position: 'relative' }}>
                    <Activity size={18} color="var(--text-muted)" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
                    <input 
                      type="number" 
                      step="any" 
                      placeholder="0.00" 
                      value={newHolding.quantity} 
                      onChange={e => setNewHolding({ ...newHolding, quantity: e.target.value })} 
                      required 
                      style={{ paddingLeft: '44px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)', borderRadius: '14px', padding: '1rem 1rem 1rem 2.8rem' }}
                    />
                  </div>
                </div>
                
                <div>
                  <label style={{ display: 'block', fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '10px', fontWeight: 600 }}>Purchase Price</label>
                  <div style={{ position: 'relative' }}>
                    <DollarSign size={18} color="var(--text-muted)" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
                    <input 
                      type="number" 
                      step="any" 
                      placeholder="0.00" 
                      value={newHolding.purchase_price} 
                      onChange={e => setNewHolding({ ...newHolding, purchase_price: e.target.value })} 
                      required 
                      style={{ paddingLeft: '44px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)', borderRadius: '14px', padding: '1rem 1rem 1rem 2.8rem' }}
                    />
                  </div>
                </div>
              </div>
              
              <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem' }}>
                <button 
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  style={{ flex: 1, padding: '1rem', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '14px', color: 'white', fontWeight: 600, cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="btn" 
                  disabled={isSubmitting}
                  style={{ 
                    flex: 2, 
                    padding: '1rem', 
                    borderRadius: '14px', 
                    fontWeight: 800, 
                    color: 'black',
                    boxShadow: '0 4px 20px rgba(0, 212, 255, 0.3)'
                  }}
                >
                  {isSubmitting ? 'Processing...' : 'Add to Portfolio'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
