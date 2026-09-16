'use client';

import React, { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';

function DepositPortal() {
  const searchParams = useSearchParams();
  const ticket = searchParams.get('ticket') || 'N/A';
  const vault = searchParams.get('vault') || '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
  const amount = searchParams.get('amount') || '0.00';

  const [status, setStatus] = useState<'idle' | 'processing' | 'success' | 'error'>('idle');
  const [txHash, setTxHash] = useState<string | null>(null);

  const handleDeposit = async () => {
    try {
      setStatus('processing');

      // Web3 deposit logic placeholder (Ethers / Viem / Wagmi integration)
      console.log(`Initiating transfer of $${amount} USDC to ${vault} for ticket ${ticket}`);

      // Simulated transaction delay
      await new Promise((resolve) => setTimeout(resolve, 2000));
      
      setTxHash('0x' + Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join(''));
      setStatus('success');
    } catch (err) {
      console.error('Deposit error:', err);
      setStatus('error');
    }
  };

  return (
    <main style={{ minHeight: '100vh', backgroundColor: '#0a0a0a', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px', fontFamily: 'sans-serif' }}>
      <div style={{ width: '100%', maxWidth: '480px', backgroundColor: '#141414', border: '1px solid #262626', borderRadius: '16px', padding: '32px', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}>
        <h1 style={{ fontSize: '20px', fontWeight: 'bold', color: '#f59e0b', marginTop: 0, marginBottom: '8px' }}>
          🔒 VouchSafe Escrow Deposit
        </h1>
        <p style={{ fontSize: '14px', color: '#a3a3a3', marginBottom: '24px' }}>
          Base L2 Trustless Escrow Vault Connection
        </p>

        <div style={{ backgroundColor: '#1f1f1f', borderRadius: '12px', padding: '16px', marginBottom: '24px', border: '1px solid #2e2e2e' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ color: '#a3a3a3', fontSize: '14px' }}>Ticket Ref:</span>
            <span style={{ fontWeight: '600', color: '#f59e0b', fontSize: '14px' }}>{ticket}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ color: '#a3a3a3', fontSize: '14px' }}>Deposit Amount:</span>
            <span style={{ fontWeight: 'bold', color: '#ffffff', fontSize: '16px' }}>${amount} USDC</span>
          </div>
          <div style={{ borderTop: '1px solid #333', paddingTop: '12px' }}>
            <span style={{ color: '#a3a3a3', fontSize: '12px', display: 'block', marginBottom: '4px' }}>Vault Address:</span>
            <span style={{ fontFamily: 'monospace', fontSize: '12px', color: '#6ee7b7', wordBreak: 'break-all' }}>{vault}</span>
          </div>
        </div>

        {status === 'success' ? (
          <div style={{ backgroundColor: '#064e3b', border: '1px solid #059669', borderRadius: '12px', padding: '16px', textAlign: 'center' }}>
            <p style={{ color: '#34d399', fontWeight: 'bold', margin: '0 0 8px 0' }}>✅ Deposit Successfully Broadcasted</p>
            <p style={{ color: '#a7f3d0', fontSize: '12px', wordBreak: 'break-all', margin: 0 }}>Tx: {txHash}</p>
          </div>
        ) : (
          <button
            onClick={handleDeposit}
            disabled={status === 'processing'}
            style={{
              width: '100%',
              padding: '14px',
              backgroundColor: status === 'processing' ? '#333333' : '#f59e0b',
              color: status === 'processing' ? '#888888' : '#000000',
              fontWeight: 'bold',
              border: 'none',
              borderRadius: '10px',
              cursor: status === 'processing' ? 'not-allowed' : 'pointer',
              fontSize: '15px'
            }}
          >
            {status === 'processing' ? 'Processing Wallet Transfer...' : 'Connect Wallet & Deposit'}
          </button>
        )}

        {status === 'error' && (
          <p style={{ color: '#f87171', fontSize: '13px', textAlign: 'center', marginTop: '12px' }}>
            ❌ Transaction failed. Please try again.
          </p>
        )}
      </div>
    </main>
  );
}

export default function DepositPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', backgroundColor: '#0a0a0a', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading Portal...</div>}>
      <DepositPortal />
    </Suspense>
  );
}
