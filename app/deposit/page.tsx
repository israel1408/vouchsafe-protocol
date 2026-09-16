'use client';

import React, { Suspense, useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';

// Base L2 USDC Contract Address
const USDC_BASE_MAINNET = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const BASE_CHAIN_ID_HEX = '0x2105'; // 8453 in Hex

declare global {
  interface Window {
    ethereum?: any;
  }
}

function DepositPortal() {
  const searchParams = useSearchParams();
  const ticket = searchParams.get('ticket') || 'N/A';
  const vault = searchParams.get('vault') || '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
  const amount = searchParams.get('amount') || '0.00';

  const [account, setAccount] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'connecting' | 'processing' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [txHash, setTxHash] = useState<string | null>(null);

  // Check if wallet is already connected
  useEffect(() => {
    if (typeof window !== 'undefined' && window.ethereum) {
      window.ethereum.request({ method: 'eth_accounts' })
        .then((accounts: string[]) => {
          if (accounts.length > 0) setAccount(accounts[0]);
        })
        .catch(() => {});
    }
  }, []);

  // Connect Wallet
  const connectWallet = async () => {
    if (typeof window === 'undefined' || !window.ethereum) {
      setErrorMessage('No Web3 wallet found. Please install MetaMask or Coinbase Wallet.');
      setStatus('error');
      return;
    }

    try {
      setStatus('connecting');
      setErrorMessage('');
      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
      setAccount(accounts[0]);
      setStatus('idle');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to connect wallet');
      setStatus('error');
    }
  };

  // Ensure user is on Base Network
  const switchToBase = async () => {
    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: BASE_CHAIN_ID_HEX }],
      });
    } catch (switchError: any) {
      // Add Base network if missing in wallet
      if (switchError.code === 4902) {
        await window.ethereum.request({
          method: 'wallet_addEthereumChain',
          params: [
            {
              chainId: BASE_CHAIN_ID_HEX,
              chainName: 'Base',
              nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
              rpcUrls: ['https://mainnet.base.org'],
              blockExplorerUrls: ['https://basescan.org'],
            },
          ],
        });
      }
    }
  };

  // Execute On-Chain USDC Deposit
  const handleDeposit = async () => {
    if (!account) {
      await connectWallet();
      return;
    }

    try {
      setStatus('processing');
      setErrorMessage('');

      // Ensure network is set to Base
      await switchToBase();

      // Encode ERC-20 transfer(address _to, uint256 _value)
      const methodId = '0xa9059cbb';
      const cleanVault = vault.toLowerCase().replace('0x', '').padStart(64, '0');
      
      // USDC uses 6 decimals ($100 = 100,000,000 units)
      const amountInUnits = Math.floor(parseFloat(amount) * 1000000);
      const hexAmount = amountInUnits.toString(16).padStart(64, '0');

      const dataPayload = `${methodId}${cleanVault}${hexAmount}`;

      // Trigger Web3 Wallet Transaction
      const hash = await window.ethereum.request({
        method: 'eth_sendTransaction',
        params: [
          {
            from: account,
            to: USDC_BASE_MAINNET,
            data: dataPayload,
          },
        ],
      });

      setTxHash(hash);
      setStatus('success');
    } catch (err: any) {
      console.error('Deposit Error:', err);
      setErrorMessage(err?.message || 'Transaction rejected or failed.');
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

        {/* Ticket Info Card */}
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

        {/* Account Status Badge */}
        {account && (
          <div style={{ marginBottom: '16px', padding: '10px', backgroundColor: '#111827', border: '1px solid #1f2937', borderRadius: '8px', fontSize: '12px', color: '#9ca3af', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Connected Wallet:</span>
            <span style={{ fontFamily: 'monospace', color: '#f59e0b', fontWeight: 'bold' }}>
              {account.substring(0, 6)}...{account.substring(account.length - 4)}
            </span>
          </div>
        )}

        {/* Action Button */}
        {status === 'success' ? (
          <div style={{ backgroundColor: '#064e3b', border: '1px solid #059669', borderRadius: '12px', padding: '16px', textAlign: 'center' }}>
            <p style={{ color: '#34d399', fontWeight: 'bold', margin: '0 0 8px 0' }}>✅ Transaction Broadcasted On-Chain!</p>
            <a
              href={`https://basescan.org/tx/${txHash}`}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#6ee7b7', fontSize: '13px', textDecoration: 'underline', wordBreak: 'break-all' }}
            >
              View on BaseScan ↗
            </a>
          </div>
        ) : (
          <button
            onClick={account ? handleDeposit : connectWallet}
            disabled={status === 'processing' || status === 'connecting'}
            style={{
              width: '100%',
              padding: '14px',
              backgroundColor: status === 'processing' || status === 'connecting' ? '#333333' : '#f59e0b',
              color: status === 'processing' || status === 'connecting' ? '#888888' : '#000000',
              fontWeight: 'bold',
              border: 'none',
              borderRadius: '10px',
              cursor: status === 'processing' || status === 'connecting' ? 'not-allowed' : 'pointer',
              fontSize: '15px'
            }}
          >
            {status === 'connecting'
              ? 'Connecting Wallet...'
              : status === 'processing'
              ? 'Confirm in Wallet...'
              : !account
              ? 'Connect Web3 Wallet'
              : `Deposit $${amount} USDC on Base`}
          </button>
        )}

        {/* Error Feedback */}
        {status === 'error' && (
          <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#450a0a', border: '1px solid #991b1b', borderRadius: '8px' }}>
            <p style={{ color: '#f87171', fontSize: '13px', margin: 0, textAlign: 'center', wordBreak: 'break-word' }}>
              ❌ {errorMessage}
            </p>
          </div>
        )}
      </div>
    </main>
  );
}

export default function DepositPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', backgroundColor: '#0a0a0a', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading Web3 Portal...</div>}>
      <DepositPortal />
    </Suspense>
  );
}
