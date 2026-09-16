import json
import logging
import asyncio
import redis.asyncio as aioredis
import discord

logger = logging.getLogger("vouchsafe.relay")

REDIS_RELAY_CHANNEL = "vouchsafe:liquidity:orders"

class LiquidityRelay:
    def __init__(self, bot: discord.Client, redis_url: str):
        """
        Initialize Redis Cross-Server Liquidity Relay.
        
        :param bot: The active discord.py Client / Bot instance.
        :param redis_url: Redis connection string (e.g. redis://redis:6379/0).
        """
        self.bot = bot
        self.redis_url = redis_url
        self.redis_pub = None
        self.redis_sub = None
        self.pubsub = None

    async def initialize(self):
        """Initialize Redis publisher and subscriber connections."""
        self.redis_pub = aioredis.from_url(self.redis_url, decode_responses=True)
        self.redis_sub = aioredis.from_url(self.redis_url, decode_responses=True)
        self.pubsub = self.redis_sub.pubsub()
        await self.pubsub.subscribe(REDIS_RELAY_CHANNEL)
        logger.info(f"Subscribed to Redis Pub/Sub relay channel: {REDIS_RELAY_CHANNEL}")

    async def publish_order(self, order_data: dict):
        """
        Publish a buy or sell order event to all partner servers via Redis.
        
        Expected order_data dictionary layout:
        {
            "origin_guild_id": 123456789,
            "origin_guild_name": "ComputeX Clearhouse",
            "ticket_id": "ESC-9482",
            "order_type": "BUY" | "SELL",
            "title": "4x RTX 4090 Host Node Cluster",
            "details": "High bandwidth, 128GB RAM, 24-hour rental available.",
            "price_usdc": 450.00,
            "vault_address": "0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
            "channel_jump_url": "https://discord.com/channels/..."
        }
        """
        if not self.redis_pub:
            await self.initialize()

        payload = json.dumps(order_data)
        await self.redis_pub.publish(REDIS_RELAY_CHANNEL, payload)
        logger.info(f"Published order {order_data.get('ticket_id')} to global relay channel.")

    async def start_listener(self):
        """
        Asynchronous loop that listens for order messages from Redis Pub/Sub
        and broadcasts embeds into designated syndication channels across partner servers.
        """
        if not self.pubsub:
            await self.initialize()

        logger.info("Liquidity relay listener loop started.")
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    data_str = message["data"]
                    try:
                        order_data = json.loads(data_str)
                        await self._handle_relayed_order(order_data)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse relay JSON payload: {data_str}")
                    except Exception as e:
                        logger.error(f"Error handling relayed order event: {e}", exc_info=True)
        except asyncio.CancelledError:
            logger.info("Liquidity relay listener task cancelled.")
        finally:
            await self.cleanup()

    async def _handle_relayed_order(self, order_data: dict):
        """Converts received order payload into a formatted Discord embed and sends to partner channels."""
        origin_guild_id = order_data.get("origin_guild_id")

        for guild in self.bot.guilds:
            # Skip broadcasting back to the guild where the order originated
            if guild.id == origin_guild_id:
                continue

            # Look for channel named 'liquidity-board' or 'global-orders' in partner server
            target_channel = (
                discord.utils.get(guild.text_channels, name="liquidity-board") or
                discord.utils.get(guild.text_channels, name="global-orders")
            )

            if not target_channel:
                continue

            order_type = str(order_data.get("order_type", "ORDER")).upper()
            embed_color = discord.Color.green() if order_type == "SELL" else discord.Color.blue()

            embed = discord.Embed(
                title=f"🌐 Global Liquidity | {order_type}: {order_data.get('title', 'Compute Offer')}",
                description=order_data.get("details", "No description provided."),
                color=embed_color
            )
            embed.add_field(name="Ticket Ref", value=f"`{order_data.get('ticket_id', 'N/A')}`", inline=True)
            embed.add_field(name="Amount / Rate", value=f"**${order_data.get('price_usdc', 0.00):,.2f} USDC**", inline=True)
            embed.add_field(name="Origin Server", value=order_data.get("origin_guild_name", "Partner Guild"), inline=True)

            if order_data.get("vault_address"):
                embed.add_field(name="Escrow Vault", value=f"`{order_data.get('vault_address')}`", inline=False)

            jump_url = order_data.get("channel_jump_url")
            if jump_url:
                embed.add_field(name="Origin Link", value=f"[Jump to Origin Ticket]({jump_url})", inline=False)

            embed.set_footer(text="VouchSafe Liquidity Network • Powered by Redis Pub/Sub")

            try:
                await target_channel.send(embed=embed)
                logger.info(f"Relayed order {order_data.get('ticket_id')} to guild: {guild.name} ({guild.id})")
            except discord.Forbidden:
                logger.warning(f"Permission denied to send message in #{target_channel.name} on guild {guild.id}")
            except Exception as e:
                logger.error(f"Failed broadcasting order to guild {guild.id}: {e}")

    async def cleanup(self):
        """Gracefully close Redis connection channels."""
        if self.pubsub:
            await self.pubsub.unsubscribe(REDIS_RELAY_CHANNEL)
            await self.pubsub.close()
        if self.redis_pub:
            await self.redis_pub.close()
        if self.redis_sub:
            await self.redis_sub.close()
        logger.info("Redis relay connections closed.")
