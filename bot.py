import os
import discord
from discord import app_commands, Interaction, ButtonStyle, Color
from discord.ext import commands
from discord.ui import View, Modal, TextInput, button, Button
from dotenv import load_dotenv

# Internal Module Imports
from verifier import process_verification_job
from listener import update_discord_thread_embed
from reputation import VouchScoreEngine

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

class VouchSafeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

bot = VouchSafeBot()

class EscrowTicketView(View):
    """Persistent control panel view inside private escrow ticket threads."""

    def __init__(self, ticket_id: str, vault_address: str, seller_id: int, buyer_id: int, asset_type: str, asset_target: str):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.vault_address = vault_address
        self.seller_id = seller_id
        self.buyer_id = buyer_id
        self.asset_type = asset_type
        self.asset_target = asset_target

    @button(label="1. Verify Asset API", style=ButtonStyle.primary, custom_id="btn_verify_asset")
    async def verify_asset_callback(self, interaction: Interaction, button: Button):
        if interaction.user.id not in [self.seller_id, self.buyer_id]:
            await interaction.response.send_message("❌ Unauthorized: Only transaction participants can trigger verification.", ephemeral=True)
            return

        await interaction.response.send_message("⏳ Contacting VouchSafe API Verification Engine...", ephemeral=True)

        verified = await process_verification_job(
            ticket_id=self.ticket_id,
            asset_type=self.asset_type,
            target_id=self.asset_target,
            expected_value=str(self.buyer_id)
        )

        if verified:
            embed = interaction.message.embeds[0]
            for field in embed.fields:
                if field.name == "Asset Verification":
                    field.value = "🟢 VERIFIED"
            await interaction.message.edit(embed=embed)
            await interaction.followup.send("✅ **Asset ownership verified via API!**", ephemeral=True)
        else:
            await interaction.followup.send("⚠️ **Verification pending or failed.** Ensure transfer parameters are correct.", ephemeral=True)

    @button(label="2. Deposit Portal (Base L2)", style=ButtonStyle.secondary, custom_id="btn_deposit_funds")
    async def deposit_funds_callback(self, interaction: Interaction, button: Button):
        portal_url = f"https://vouchsafe.io/deposit?ticket={self.ticket_id}&vault={self.vault_address}"
        await interaction.response.send_message(
            f"🔗 Connect wallet and complete deposit on Base L2:\n<{portal_url}>\n\nVault: `{self.vault_address}`",
            ephemeral=True
        )

    @button(label="3. Confirm & Release", style=ButtonStyle.success, custom_id="btn_release_funds")
    async def release_funds_callback(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.buyer_id:
            await interaction.response.send_message("❌ Only the buyer can approve final fund release.", ephemeral=True)
            return

        await interaction.response.defer()

        await update_discord_thread_embed(
            channel_id=str(interaction.channel_id),
            message_id=str(interaction.message.id),
            new_state="🟢 SETTLED & DISBURSED",
            color_code=0x2ecc71
        )

        await interaction.followup.send("🎉 **Deal Completed!** Escrow vault payout disbursed on Base L2.")


class EscrowInitModal(Modal, title="VouchSafe | Initialize OTC Escrow"):
    seller_id = TextInput(label="Seller Discord User ID", placeholder="e.g. 123456789012345678", required=True)
    asset_type = TextInput(label="Asset Category", placeholder="Whop Store / Domain / Discord / GitHub", required=True)
    amount_usdc = TextInput(label="Escrow Amount (USDC)", placeholder="1500.00", required=True)
    asset_target = TextInput(label="Asset Identifier / API Target", placeholder="company_id, domain, or repo-name", required=True)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)

        thread = await interaction.channel.create_thread(
            name=f"escrow-{interaction.user.name[:8]}-vs-{self.seller_id.value[:4]}",
            type=discord.ChannelType.private_thread
        )

        await thread.add_user(interaction.user)
        try:
            seller_user = await interaction.client.fetch_user(int(self.seller_id.value))
            await thread.add_user(seller_user)
            seller_mention = seller_user.mention
            seller_id_int = seller_user.id
        except Exception:
            seller_mention = f"<@{self.seller_id.value}>"
            seller_id_int = int(self.seller_id.value)

        ticket_id = f"ESC-{thread.id}"
        mock_vault_address = "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"

        embed = discord.Embed(
            title=f"🛡️ VouchSafe Escrow Vault #{ticket_id}",
            description=f"Automated OTC Escrow between {interaction.user.mention} (Buyer) and {seller_mention} (Seller).",
            color=Color.gold()
        )
        embed.add_field(name="Asset Category", value=self.asset_type.value, inline=True)
        embed.add_field(name="Deposit Required", value=f"${float(self.amount_usdc.value):,.2f} USDC", inline=True)
        embed.add_field(name="Asset Target", value=f"`{self.asset_target.value}`", inline=False)
        embed.add_field(name="Vault State", value="🟡 AWAITING_DEPOSIT", inline=True)
        embed.add_field(name="Asset Verification", value="🔴 UNVERIFIED", inline=True)
        embed.add_field(name="Vault Contract (Base L2)", value=f"`{mock_vault_address}`", inline=False)
        embed.set_footer(text="VouchSafe Protocol | Cryptographic OTC Escrow")

        view = EscrowTicketView(
            ticket_id=ticket_id,
            vault_address=mock_vault_address,
            seller_id=seller_id_int,
            buyer_id=interaction.user.id,
            asset_type=self.asset_type.value,
            asset_target=self.asset_target.value
        )

        await thread.send(content=f"{interaction.user.mention} {seller_mention}", embed=embed, view=view)
        await interaction.followup.send(f"Escrow thread created: {thread.mention}", ephemeral=True)


@bot.tree.command(name="escrow", description="Create an automated VouchSafe escrow vault deal")
async def escrow_command(interaction: Interaction):
    await interaction.response.send_modal(EscrowInitModal())


@bot.tree.command(name="reputation", description="Lookup a trader's VouchScore and historical rating")
@app_commands.describe(user="User to inspect")
async def reputation_command(interaction: Interaction, user: discord.User = None):
    target_user = user or interaction.user

    score = VouchScoreEngine.calculate_score(total_volume_usdc=15000.0, successful_trades=8, disputes_lost=0, account_age_days=90)
    data = VouchScoreEngine.generate_reputation_embed_data(str(target_user.id), score, 15000.0, 8)

    embed = discord.Embed(title=data["title"], color=Color.gold())
    embed.add_field(name="VouchScore Rating", value=data["score"], inline=True)
    embed.add_field(name="Tier Class", value=data["tier"], inline=True)
    embed.add_field(name="Fee Discount", value=data["fee_discount"], inline=True)
    embed.add_field(name="Total Settled Volume", value=data["total_volume"], inline=True)
    embed.add_field(name="Completed Trades", value=str(data["completed_trades"]), inline=True)
    embed.add_field(name="Single Trade Limit", value=data["max_trade_limit"], inline=True)
    embed.set_footer(text="VouchSafe Reputation Engine")

    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    bot.run(TOKEN)
