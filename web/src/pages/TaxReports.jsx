import { useState } from 'react'
import { apiFetch } from '../lib/api.js'
import { FileText, Download, Calendar, CheckCircle2, ShieldCheck, Info } from 'lucide-react'

export default function TaxReports() {
    const [loading, setLoading] = useState(false)
    const [report, setReport] = useState(null)

    const generateReport = async () => {
        setLoading(true)
        try {
            const data = await apiFetch('/api/portfolio/tax-report', { auth: true })
            setReport(data.data)
        } catch (err) {
            console.error('Tax report error:', err)
            alert('Failed to generate report: ' + err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="page-container" style={{ maxWidth: '1000px', margin: '0 auto', padding: '2rem' }}>
            <header style={{ marginBottom: '2.5rem' }}>
                <h1 style={{ fontSize: '2.4rem', fontWeight: 800, marginBottom: '0.5rem' }}>Tax Reporting</h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>Generate tax-compliant reports for your crypto transactions and capital gains.</p>
            </header>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                <div className="card" style={{ padding: '2.5rem', borderRadius: '24px', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    <div style={{ width: '60px', height: '60px', borderRadius: '18px', background: 'rgba(0, 212, 255, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '0.5rem' }}>
                        <FileText size={32} color="var(--primary)" />
                    </div>
                    <h3 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Transaction History Report</h3>
                    <p style={{ color: 'var(--text-muted)', lineHeight: 1.6 }}>Download a full CSV export of all your portfolio transactions, including cost basis, purchase dates, and realized P&L calculations.</p>

                    <div style={{ marginTop: 'auto' }}>
                        <button
                            onClick={generateReport}
                            disabled={loading}
                            className="btn-primary"
                            style={{ width: '100%', padding: '16px', borderRadius: '16px', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}
                        >
                            {loading ? 'Processing...' : <><Download size={20} /> Generate CSV Report</>}
                        </button>
                    </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    <div className="card" style={{ padding: '1.5rem', borderRadius: '20px', display: 'flex', gap: '1rem', alignItems: 'center' }}>
                        <div style={{ background: 'rgba(0, 230, 118, 0.1)', padding: '10px', borderRadius: '12px' }}>
                            <ShieldCheck size={24} color="#00e676" />
                        </div>
                        <div>
                            <div style={{ fontWeight: 700, fontSize: '1rem' }}>Data Integrity Verified</div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>All transactions are verified against blockchain data.</div>
                        </div>
                    </div>

                    <div className="card" style={{ padding: '1.5rem', borderRadius: '20px', display: 'flex', gap: '1rem', alignItems: 'center' }}>
                        <div style={{ background: 'rgba(123, 47, 239, 0.1)', padding: '10px', borderRadius: '12px' }}>
                            <Calendar size={24} color="var(--secondary)" />
                        </div>
                        <div>
                            <div style={{ fontWeight: 700, fontSize: '1rem' }}>2024 Tax Year Ready</div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Report formatted for current regulatory requirements.</div>
                        </div>
                    </div>

                    <div className="card" style={{ padding: '1.5rem', borderRadius: '20px', background: 'linear-gradient(135deg, rgba(255,165,0,0.05), rgba(255,69,0,0.05))', border: '1px solid rgba(255,165,0,0.1)' }}>
                        <div style={{ display: 'flex', gap: '10px', marginBottom: '8px' }}>
                            <Info size={18} color="#ffa500" />
                            <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#ffa500' }}>Disclaimer</div>
                        </div>
                        <p style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.6)', lineHeight: 1.5 }}>
                            This report is for informational purposes only and does not constitute professional tax advice. Always consult with a tax professional.
                        </p>
                    </div>
                </div>
            </div>

            {report && (
                <div style={{ marginTop: '2.5rem', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                    {/* Summary Cards */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
                        <div className="card" style={{ padding: '1.5rem', borderRadius: '20px', textAlign: 'center' }}>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '5px' }}>Realized Gain</div>
                            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#00e676' }}>
                                ${report.summary?.total_realized_gain?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                            </div>
                        </div>
                        <div className="card" style={{ padding: '1.5rem', borderRadius: '20px', textAlign: 'center' }}>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '5px' }}>Realized Loss</div>
                            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ff5252' }}>
                                ${report.summary?.total_realized_loss?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                            </div>
                        </div>
                        <div className="card" style={{ padding: '1.5rem', borderRadius: '20px', textAlign: 'center' }}>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '5px' }}>Unrealized P&L</div>
                            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: (report.summary?.total_unrealized_pnl >= 0 ? 'var(--primary)' : '#ff5252') }}>
                                ${report.summary?.total_unrealized_pnl?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                            </div>
                        </div>
                        <div className="card" style={{ padding: '1.5rem', borderRadius: '20px', textAlign: 'center' }}>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '5px' }}>Total Assets</div>
                            <div style={{ fontSize: '1.4rem', fontWeight: 800 }}>{report.num_assets || 0}</div>
                        </div>
                    </div>

                    {/* Report Status */}
                    <div className="card" style={{ padding: '2rem', borderRadius: '24px', border: '1px solid var(--primary)', background: 'rgba(0, 212, 255, 0.03)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                <CheckCircle2 size={24} color="var(--primary)" />
                                <div>
                                    <h4 style={{ fontWeight: 700, fontSize: '1.1rem' }}>Report Successfully Generated</h4>
                                    <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                                        {report.message || `Processed ${report.num_assets} asset histories with FIFO cost-basis.`}
                                    </p>
                                </div>
                            </div>
                            <div style={{ fontSize: '0.85rem', textAlign: 'right', display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-end' }}>
                                <span style={{ color: 'var(--text-muted)' }}>Ready for download</span>
                                {report.csv_url && (
                                    <a href={`${import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001'}${report.csv_url}`} 
                                       target="_blank" rel="noopener noreferrer" 
                                       style={{ background: 'var(--primary)', color: '#000', padding: '8px 16px', borderRadius: '8px', textDecoration: 'none', fontWeight: 600, display: 'inline-block' }}>
                                        Download CSV
                                    </a>
                                )}
                            </div>
                        </div>
                    </div>

                    {report.details && report.details.length > 0 && (
                        <div className="card" style={{ padding: '1.5rem', borderRadius: '24px', overflowX: 'auto' }}>
                            <h3 style={{ marginBottom: '1.5rem', fontWeight: 700 }}>Transaction Logic & PnL</h3>
                            <table className="market-table" style={{ width: '100%', minWidth: '800px', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr>
                                        <th style={{ textAlign: 'left', padding: '12px', borderBottom: '1px solid var(--border)' }}>Date</th>
                                        <th style={{ textAlign: 'left', padding: '12px', borderBottom: '1px solid var(--border)' }}>Asset</th>
                                        <th style={{ textAlign: 'left', padding: '12px', borderBottom: '1px solid var(--border)' }}>Type</th>
                                        <th style={{ textAlign: 'right', padding: '12px', borderBottom: '1px solid var(--border)' }}>Qty</th>
                                        <th style={{ textAlign: 'right', padding: '12px', borderBottom: '1px solid var(--border)' }}>Price/Cost</th>
                                        <th style={{ textAlign: 'right', padding: '12px', borderBottom: '1px solid var(--border)' }}>Realized P&L</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {report.details.map((row, idx) => (
                                        <tr key={idx}>
                                            <td style={{ padding: '12px', borderBottom: '1px solid rgba(255,255,255,0.05)', color: 'var(--text-muted)' }}>
                                                {row.date === 'HOLDING' ? 'Current Holding' : new Date(row.date || row.timestamp).toLocaleDateString()}
                                            </td>
                                            <td style={{ padding: '12px', borderBottom: '1px solid rgba(255,255,255,0.05)', fontWeight: 600 }}>{row.coin_id?.toUpperCase()}</td>
                                            <td style={{ padding: '12px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                                <span style={{ 
                                                    padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 700,
                                                    background: row.type === 'BUY' ? 'rgba(0, 230, 118, 0.1)' : 
                                                               row.type === 'SELL' ? 'rgba(255, 82, 82, 0.1)' : 
                                                               'rgba(123, 47, 239, 0.1)',
                                                    color: row.type === 'BUY' ? '#00e676' : 
                                                           row.type === 'SELL' ? '#ff5252' : 
                                                           'var(--secondary)'
                                                }}>
                                                    {row.type}
                                                </span>
                                            </td>
                                            <td style={{ padding: '12px', borderBottom: '1px solid rgba(255,255,255,0.05)', textAlign: 'right' }}>{Number(row.qty || 0).toLocaleString(undefined, { maximumFractionDigits: 6 })}</td>
                                            <td style={{ padding: '12px', borderBottom: '1px solid rgba(255,255,255,0.05)', textAlign: 'right' }}>${Number(row.price || row.cost_basis || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                            <td style={{ padding: '12px', borderBottom: '1px solid rgba(255,255,255,0.05)', textAlign: 'right', fontWeight: 600 }} className={row.realized_pnl > 0 ? 'positive' : (row.realized_pnl < 0 ? 'negative' : '')}>
                                                {row.realized_pnl !== undefined && row.realized_pnl !== 0 ? `$${Number(row.realized_pnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 
                                                 row.unrealized_pnl !== undefined ? `($${Number(row.unrealized_pnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })})` : '-'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
