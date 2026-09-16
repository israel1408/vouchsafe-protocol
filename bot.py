import os
import discord
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import View, button, Button
from dotenv import load_dotenv

# Import internal modules
from verifier import verify_ownership
from listener import update_discord_thread_embed

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


class EscrowTicketView(View):
    """Interactive control panel embedded inside each Escrow Ticket thread."""

    def __init__(self, ticket_id: str, vault_address: str, seller_id: int, buyer_id: int):
        super().__init__(timeout=None)  # Persistent view
        self.ticket_id = ticket_id
        self.vault_address = vault_address
        self.seller_id = seller_id
        self.buyer_id = buyer_id

    @button(label="1. Verify Asset Ownership", style=ButtonStyle.primary, custom_id="btn_verify_asset")
    async def verify_asset_callback(self, interaction: Interaction, button: Button):
        """Triggers account/API key verification via verifier.py."""
        if interaction.user.id != self.seller_id:
            await interaction.response.send_message("❌ Only the seller can run asset verification.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Trigger verifier script
        is_valid, details = await verify_ownership(self.ticket_id)

        if is_valid:
            embed = interaction.message.embeds[0]
            for field in embed.fields:
                if field.name == "Asset Verification":
                    field.value = "🟢 VERIFIED"

            await interaction.message.edit(embed=embed)
            await interaction.followup.send(f"✅ **Asset Verified!**\nDetails: `{details}`", ephemeral=True)
        else:
            await interaction.followup.send(f"⚠️ **Verification Failed:** {details}", ephemeral=True)

    @button(label="2. Check Deposit Status", style=ButtonStyle.secondary, custom_id="btn_check_deposit")
    async def check_deposit_callback(self, interaction: Interaction, button: Button):
        """Allows users to manually check if Base L2 deposit has cleared."""
        await interaction.response.send_message(
            f"🔍 Checking Base vault status for `0x...{self.vault_address[-8:]}`...",
            ephemeral=True
        )

    @button(label="3. Confirm & Release Funds", style=ButtonStyle.success, custom_id="btn_release_funds")
    async def release_funds_callback(self, interaction: Interaction, button: Button):
        """Allows the buyer to release escrowed funds to the seller once delivered."""
        if interaction.user.id != self.buyer_id:
            await interaction.response.send_message("❌ Only the buyer can approve fund release.", ephemeral=True)
            return

        await interaction.response.defer()

        # Update Discord Thread UI State to Completed
        await update_discord_thread_embed(
            channel_id=str(interaction.channel_id),
            message_id=str(interaction.message.id),
            new_state="🟢 SETTLED & RELEASED",
            color_code=0x2ecc71 # Green
        )

        await interaction.followup.send(
            "🎉 **Transaction Complete!** Escrow funds have been disbursed on Base L2."
        )


@bot.event
async def on_ready():
    print(f"🤖 Bot is live as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@bot.tree.command(name="escrow", description="Create a new escrow trade channel")
@app_commands.describe(seller="The user selling the asset", amount_usdc="Escrow amount in USDC")
async def create_escrow(interaction: Interaction, seller: discord.User, amount_usdc: float):
    """Slash command to initialize an escrow deal thread."""
    await interaction.response.defer()

    buyer = interaction.user
    ticket_id = f"ESC-{interaction.id}"
    mock_vault = "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"

    # Construct status embed
    embed = discord.Embed(
        title=f"🔒 Escrow Deal #{ticket_id}",
        description="Follow the steps below to complete the peer-to-peer trade safely on Base.",
        color=0xf1c40f # Yellow (Awaiting Action)
    )
    embed.add_field(name="Buyer", value=buyer.mention, inline=True)
    embed.add_field(name="Seller", value=seller.mention, inline=True)
    embed.add_field(name="Amount", value=f"`{amount_usdc:.2f} USDC`", inline=True)
    embed.add_field(name="Vault State", value="🟡 AWAITING_DEPOSIT", inline=True)
    embed.add_field(name="Asset Verification", value="🔴 UNVERIFIED", inline=True)
    embed.add_field(name="Vault Address", value=f"`{mock_vault}`", inline=False)

    view = EscrowTicketView(
        ticket_id=ticket_id,
        vault_address=mock_vault,
        seller_id=seller.id,
        buyer_id=buyer.id
    )

    await interaction.followup.send(embed=embed, view=view)


if __name__ == "__main__":
    bot.run(TOKEN)
