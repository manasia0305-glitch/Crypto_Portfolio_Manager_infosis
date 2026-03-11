import React from 'react';

const HeatmapItem = ({ coin }) => {
  const change = coin.change_24h || 0;
  const isPositive = change >= 0;
  
  // Calculate background color intensity based on change
  const intensity = Math.min(Math.abs(change) / 10, 1); // Max intensity at 10% change
  const backgroundColor = isPositive 
    ? `rgba(0, 230, 118, ${0.2 + intensity * 0.8})` 
    : `rgba(255, 23, 68, ${0.2 + intensity * 0.8})`;

  return (
    <div 
      style={{
        background: backgroundColor,
        padding: '1rem',
        borderRadius: '12px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100px',
        transition: 'transform 0.2s',
        cursor: 'pointer',
        border: '1px solid rgba(255,255,255,0.1)'
      }}
      onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.05)'}
      onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
    >
      <img src={coin.image} alt={coin.name} style={{ width: 24, height: 24, marginBottom: '8px' }} />
      <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{coin.symbol.toUpperCase()}</span>
      <span style={{ fontSize: '0.8rem' }}>{isPositive ? '+' : ''}{change.toFixed(2)}%</span>
    </div>
  );
};

export default function MarketHeatmap({ data }) {
  if (!data || data.length === 0) return <div>No data available for heatmap.</div>;

  return (
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', 
      gap: '12px',
      marginTop: '1.5rem'
    }}>
      {data.map(coin => (
        <HeatmapItem key={coin.coin_id} coin={coin} />
      ))}
    </div>
  );
}
