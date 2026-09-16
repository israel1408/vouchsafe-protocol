import os
import logging
import asyncpg

logger = logging.getLogger("vouchsafe.db")

# Global connection pool instance
pool = None


async def init_db(dsn: str):
    """Initializes PostgreSQL connection pool and ensures required tables exist."""
    global pool
    if not dsn:
        logger.warning("DATABASE_URL not set. Database functions will run in bypass mode.")
        return

    # Fix legacy dialect prefix if present
    if dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql://", 1)

    try:
        pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=10)
        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id VARCHAR(64) PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    creator_id BIGINT NOT NULL,
                    order_type VARCHAR(10) NOT NULL,
                    amount NUMERIC(18, 4) NOT NULL,
                    title TEXT NOT NULL,
                    vault_address VARCHAR(128) NOT NULL,
                    status VARCHAR(20) DEFAULT 'PENDING',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS reputation (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    rating INT CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        logger.info("PostgreSQL database pool established and tables verified.")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        pool = None


async def create_ticket(
    ticket_id: str,
    guild_id: int,
    creator_id: int,
    order_type: str,
    amount: float,
    title: str,
    vault_address: str,
):
    """Persists a newly created escrow ticket into PostgreSQL."""
    if not pool:
        logger.warning(f"Database pool offline. Ticket {ticket_id} skipped database write.")
        return

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tickets (ticket_id, guild_id, creator_id, order_type, amount, title, vault_address, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'PENDING')
            ON CONFLICT (ticket_id) DO NOTHING;
            """,
            ticket_id,
            int(guild_id),
            int(creator_id),
            order_type,
            amount,
            title,
            vault_address,
        )


async def get_ticket(ticket_id: str):
    """Retrieves an existing escrow ticket record by ID."""
    if not pool:
        return None

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT ticket_id, title, status, amount, vault_address FROM tickets WHERE ticket_id = $1;",
            ticket_id,
        )
        return dict(row) if row else None


async def update_ticket_status(ticket_id: str, status: str):
    """Updates the processing status of an active ticket."""
    if not pool:
        return

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE tickets SET status = $1 WHERE ticket_id = $2;",
            status,
            ticket_id,
        )


async def update_reputation(user_id: int, rating: int, comment: str):
    """Records user vouches and reputation updates."""
    if not pool:
        return

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO reputation (user_id, rating, comment)
            VALUES ($1, $2, $3);
            """,
            int(user_id),
            rating,
            comment,
        )
