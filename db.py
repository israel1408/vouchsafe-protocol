import os
import asyncpg
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/vouchsafe")

class Database:
    _pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
        return cls._pool

    @classmethod
    async def close(cls):
        if cls._pool:
            await cls._pool.close()
            cls._pool = None

    @classmethod
    async def ensure_user(cls, discord_id: str):
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (discord_id) VALUES ($1)
                ON CONFLICT (discord_id) DO NOTHING;
                """,
                discord_id
            )

    @classmethod
    async def create_ticket(cls, ticket_data: Dict[str, Any]):
        pool = await cls.get_pool()
        await cls.ensure_user(ticket_data["buyer_discord_id"])
        await cls.ensure_user(ticket_data["seller_discord_id"])

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO escrow_tickets (
                    ticket_id, guild_id, thread_id, message_id,
                    buyer_discord_id, seller_discord_id, vault_address,
                    asset_type, asset_target, amount_usdc, state
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11);
                """,
                ticket_data["ticket_id"], ticket_data["guild_id"], ticket_data["thread_id"],
                ticket_data["message_id"], ticket_data["buyer_discord_id"], ticket_data["seller_discord_id"],
                ticket_data["vault_address"], ticket_data["asset_type"], ticket_data["asset_target"],
                ticket_data["amount_usdc"], ticket_data.get("state", "AWAITING_DEPOSIT")
            )

    @classmethod
    async def update_ticket_state(cls, ticket_id: str, new_state: str):
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE escrow_tickets SET state = $1 WHERE ticket_id = $2;",
                new_state, ticket_id
            )

    @classmethod
    async def get_ticket(cls, ticket_id: str) -> Optional[Dict[str, Any]]:
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM escrow_tickets WHERE ticket_id = $1;", ticket_id)
            return dict(row) if row else None

    @classmethod
    async def record_completed_trade(cls, ticket_id: str):
        pool = await cls.get_pool()
        ticket = await cls.get_ticket(ticket_id)
        if not ticket:
            return

        buyer = ticket["buyer_discord_id"]
        seller = ticket["seller_discord_id"]
        amount = float(ticket["amount_usdc"])
        guild_id = ticket["guild_id"]

        async with pool.acquire() as conn:
            async with conn.transaction():
                # 1. Update ticket status
                await conn.execute("UPDATE escrow_tickets SET state = 'SETTLED' WHERE ticket_id = $1;", ticket_id)

                # 2. Update buyer stats
                await conn.execute(
                    """
                    UPDATE users 
                    SET total_volume_usdc = total_volume_usdc + $1, successful_trades = successful_trades + 1 
                    WHERE discord_id = $2;
                    """,
                    amount, buyer
                )

                # 3. Update seller stats
                await conn.execute(
                    """
                    UPDATE users 
                    SET total_volume_usdc = total_volume_usdc + $1, successful_trades = successful_trades + 1 
                    WHERE discord_id = $2;
                    """,
                    amount, seller
                )

                # 4. Accrue 0.4% server owner rev-share
                server_fee = amount * 0.004
                await conn.execute(
                    """
                    UPDATE server_rev_share 
                    SET unpaid_usdc_balance = unpaid_usdc_balance + $1, total_earned_usdc = total_earned_usdc + $1 
                    WHERE guild_id = $2;
                    """,
                    server_fee, guild_id
                )
