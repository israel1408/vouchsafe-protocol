import os
import asyncio
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv
from aiohttp import web

# Local protocol modules
from db import init_db, create_ticket, get_ticket, update_ticket_status, update_reputation
from verifier import verify_host_node
from reputation import calculate_vouch_score
from relay import LiquidityRelay

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL")
TREASURY_WALLET_ADDRESS = os.getenv(
    "TREASURY_WALLET_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
)
VERCEL_DEPOSIT_URL = os.getenv("VERCEL_DEPOSIT_URL", "https://vouchsafe.vercel.app/deposit")
PORT = int(os.getenv("PORT", 8080))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vouchsafe.bot")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
relay = LiquidityRelay(bot, REDIS_URL)


# ==============================================================================
# RENDER HEALTH CHECK SERVER
# ==============================================================================

async def health_check(request):
    """HTTP endpoint required by Render Web Service health checks."""
    return web.Response(text="VouchSafe Protocol Web Service is online.", status=200)


async def start_web_server():
    """Starts web server bound to Render's dynamic PORT before Discord login."""
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Render HTTP health check server active on port {PORT}")


@bot.event
async def on_ready():
    logger.info(f"VouchSafe Bot online as {bot.user} (ID: {bot.user.id})")

    try:
        await init_db(DATABASE_URL)
        logger.info("PostgreSQL database pool established.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    try:
        await relay.initialize()
        bot.loop.create_task(relay.start_listener())
        logger.info("Global liquidity relay active and listening.")
    except Exception as e:
        logger.error(f"Failed to launch LiquidityRelay: {e}")


# ==============================================================================
# ESCROW & REPUTATION COMMANDS
# ==============================================================================

@bot.command(name="escrow")
async def create_escrow_cmd(ctx: commands.Context, order_type: str, amount: float, *, title: str):
    order_type_upper = order_type.upper()
    if order_type_upper not in ["BUY", "SELL"]:
        await ctx.send("❌ Order type must be `BUY` or `SELL`.")
        return

    ticket_id = f"ESC-{ctx.message.id % 100000:05d}"

    # Properly awaiting database row insertion into PostgreSQL
    try:
        await create_ticket(
            ticket_id=ticket_id,
            guild_id=ctx.guild.id,
            creator_id=ctx.author.id,
            order_type=order_type_upper,
            amount=amount,
            title=title,
            vault_address=TREASURY_WALLET_ADDRESS
        )
        logger.info(f"Ticket {ticket_id} persisted to database.")
    except Exception as e:
        logger.error(f"Failed to save ticket {ticket_id} to DB: {e}")

    deposit_link = f"{VERCEL_DEPOSIT_URL}?ticket={ticket_id}&vault={TREASURY_WALLET_ADDRESS}&amount={amount}"
    embed = discord.Embed(
        title=f"🔒 Escrow Vault Ticket | {ticket_id}",
        description=f"**Title:** {title}\n**Type:** `{order_type_upper}`\n**Amount:** **${amount:,.2f} USDC**",
        color=discord.Color.gold()
    )
    embed.add_field(name="Target Chain", value="Base L2", inline=True)
    embed.add_field(name="Escrow Vault", value=f"`{TREASURY_WALLET_ADDRESS}`", inline=False)
    embed.add_field(name="Deposit Portal", value=f"[Connect Wallet & Deposit]({deposit_link})", inline=False)
    embed.set_footer(text="VouchSafe Protocol • Base L2 Trustless Escrow")

    ticket_msg = await ctx.send(embed=embed)

    order_payload = {
        "origin_guild_id": ctx.guild.id,
        "origin_guild_name": ctx.guild.name,
        "ticket_id": ticket_id,
        "order_type": order_type_upper,
        "title": title,
        "details": f"Created by @{ctx.author.name} in #{ctx.channel.name}",
        "price_usdc": amount,
        "vault_address": TREASURY_WALLET_ADDRESS,
        "channel_jump_url": ticket_msg.jump_url
    }

    await relay.publish_order(order_payload)
    await ctx.message.add_reaction("🌐")


@bot.command(name="status")
async def get_status_cmd(ctx: commands.Context, ticket_id: str):
    ticket = await get_ticket(ticket_id)
    if not ticket:
        await ctx.send(f"❌ Ticket `{ticket_id}` not found.")
        return

    embed = discord.Embed(title=f"📋 Ticket Status | {ticket_id}", color=discord.Color.blue())
    embed.add_field(name="Title", value=ticket["title"], inline=False)
    embed.add_field(name="Status", value=f"`{ticket['status']}`", inline=True)
    embed.add_field(name="Amount", value=f"${ticket['amount']:,.2f} USDC", inline=True)
    embed.add_field(name="Vault", value=f"`{ticket['vault_address']}`", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="verify")
async def verify_cmd(ctx: commands.Context, ticket_id: str, host_endpoint: str):
    await ctx.send(f"🔍 Running verification checks on `{host_endpoint}` for ticket `{ticket_id}`...")
    is_valid, report = await verify_host_node(host_endpoint)
    
    if is_valid:
        await update_ticket_status(ticket_id, "VERIFIED")
        embed = discord.Embed(
            title="✅ Host Node Verification Passed",
            description=f"Ticket `{ticket_id}` assets verified.\n```\n{report}\n```",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="❌ Verification Failed",
            description=f"Ticket `{ticket_id}` failed compliance checks.\n```\n{report}\n```",
            color=discord.Color.red()
        )
    await ctx.send(embed=embed)


@bot.command(name="vouch")
async def vouch_cmd(ctx: commands.Context, target_user: discord.Member, rating: int, *, comment: str = "No comment"):
    if rating < 1 or rating > 5:
        await ctx.send("❌ Rating must be between 1 and 5 stars.")
        return
    if target_user.id == ctx.author.id:
        await ctx.send("❌ You cannot vouch for yourself.")
        return

    new_score = await calculate_vouch_score(target_user.id, rating)
    await update_reputation(target_user.id, rating, comment)

    embed = discord.Embed(
        title="⭐ Vouch Recorded",
        description=f"Vouched for {target_user.mention} ({rating}/5 Stars)\n*\"{comment}\"*",
        color=discord.Color.gold()
    )
    embed.add_field(name="Updated VouchScore", value=f"**{new_score:.1f} / 100.0**", inline=True)
    await ctx.send(embed=embed)


# ==============================================================================
# ASYNC MAIN ENTRYPOINT
# ==============================================================================

async def main():
    await start_web_server()

    if not DISCORD_BOT_TOKEN:
        logger.error("CRITICAL: DISCORD_BOT_TOKEN is missing from environment variables!")
        await asyncio.Event().wait()
        return

    try:
        async with bot:
            await bot.start(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        logger.error("CRITICAL: Discord login failed! DISCORD_BOT_TOKEN is invalid or malformed.")
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
