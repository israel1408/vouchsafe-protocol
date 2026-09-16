-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users and VouchScore Reputation State
CREATE TABLE IF NOT EXISTS users (
    discord_id VARCHAR(32) PRIMARY KEY,
    wallet_address VARCHAR(42),
    vouch_score INT DEFAULT 100,
    total_volume_usdc NUMERIC(12, 2) DEFAULT 0.00,
    successful_trades INT DEFAULT 0,
    disputes_lost INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Active & Historical Escrow Tickets
CREATE TYPE vault_state AS ENUM (
    'AWAITING_DEPOSIT',
    'FUNDS_LOCKED',
    'VERIFYING_ASSET',
    'SETTLED',
    'DISPUTED',
    'REFUNDED'
);

CREATE TABLE IF NOT EXISTS escrow_tickets (
    ticket_id VARCHAR(64) PRIMARY KEY,
    guild_id VARCHAR(32) NOT NULL,
    thread_id VARCHAR(32) NOT NULL,
    message_id VARCHAR(32) NOT NULL,
    buyer_discord_id VARCHAR(32) REFERENCES users(discord_id),
    seller_discord_id VARCHAR(32) REFERENCES users(discord_id),
    vault_address VARCHAR(42) UNIQUE,
    asset_type VARCHAR(32) NOT NULL,
    asset_target VARCHAR(255) NOT NULL,
    amount_usdc NUMERIC(12, 2) NOT NULL,
    state vault_state DEFAULT 'AWAITING_DEPOSIT',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Discord Server Owner Rev-Share Tracking
CREATE TABLE IF NOT EXISTS server_rev_share (
    guild_id VARCHAR(32) PRIMARY KEY,
    owner_discord_id VARCHAR(32) NOT NULL,
    payout_wallet VARCHAR(42) NOT NULL,
    unpaid_usdc_balance NUMERIC(12, 2) DEFAULT 0.00,
    total_earned_usdc NUMERIC(12, 2) DEFAULT 0.00
);
