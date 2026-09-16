import json
import logging
import redis.asyncio as aioredis

logger = logging.getLogger("vouchsafe.relay")

class LiquidityRelay:
    """Cross-server global liquidity order syndication via Redis Pub/Sub."""
    
    def __init__(self, bot, redis_url: str):
        self.bot = bot
        self.redis_url = redis_url
        self.redis = None
        self.pubsub = None

    async def initialize(self):
        """Establishes async connection to Upstash/Railway Redis instance."""
        try:
            self.redis = aioredis.from_url(
                self.redis_url, 
                decode_responses=True,
                socket_timeout=10.0
            )
            self.pubsub = self.redis.pubsub()
            logger.info("LiquidityRelay Redis client connected successfully.")
        except Exception as e:
            logger.error(f"LiquidityRelay Redis connection failed: {e}")
            self.redis = None
            self.pubsub = None

    async def publish_order(self, order_payload: dict):
        """Publishes order payload to the global 'vouchsafe:orders' channel."""
        if not self.redis:
            logger.warning("Redis client offline. Order publish skipped.")
            return

        try:
            message_str = json.dumps(order_payload)
            await self.redis.publish("vouchsafe:orders", message_str)
            logger.info(f"Published ticket {order_payload.get('ticket_id')} to global relay.")
        except Exception as e:
            logger.error(f"Failed to publish order to Redis: {e}")

    async def start_listener(self):
        """Subscribes to global orders channel and listens for incoming cross-server broadcasts."""
        if not self.pubsub:
            logger.warning("PubSub connection unavailable. Listener not started.")
            return

        try:
            await self.pubsub.subscribe("vouchsafe:orders")
            logger.info("LiquidityRelay listening on channel 'vouchsafe:orders'...")
            
            async for message in self.pubsub.listen():
                if message and message.get("type") == "message":
                    data = json.loads(message["data"])
                    ticket_id = data.get("ticket_id")
                    origin_guild = data.get("origin_guild_name", "Unknown Server")
                    logger.info(f"Relayed order received from [{origin_guild}]: Ticket {ticket_id}")
        except Exception as e:
            logger.error(f"LiquidityRelay listener encountered error: {e}")
