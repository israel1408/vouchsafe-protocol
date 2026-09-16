import React from 'react';

export default function Home() {
  return (
    <main style={{ minHeight: '100vh', backgroundColor: '#0a0a0a', color: '#ffffff', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '20px', fontFamily: 'sans-serif' }}>
      <div style={{ textAlign: 'center', maxWidth: '500px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 'bold', color: '#f59e0b', marginBottom: '12px' }}>
          🔒 VouchSafe Protocol
        </h1>
        <p style={{ color: '#a3a3a3', fontSize: '15px', lineHeight: '1.6', marginBottom: '24px' }}>
          Base L2 Trustless OTC Escrow & Reputation Clearinghouse.
        </p>
        <div style={{ padding: '16px', backgroundColor: '#141414', border: '1px solid #262626', borderRadius: '12px', fontSize: '13px', color: '#6ee7b7' }}>
          ✅ Deposit portal active. Access escrow links directly via Discord using <code style={{ color: '#f59e0b' }}>!escrow</code>.
        </div>
      </div>
    </main>
  );
}
