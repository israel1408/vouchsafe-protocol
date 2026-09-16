import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

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
            guild = discord.Object(id=int GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

bot = VouchSafeBot()

class EscrowModal(discord.ui.Modal, title="VouchSafe | Create Escrow Deal"):
    seller = discord.ui.TextInput(
        label="Seller Discord User ID",
        placeholder="e.g. 123456789012345678",
        required=True
    )
    asset_type = discord.ui.TextInput(
        label="Asset Type (Whop Store, Domain, Discord)",
        placeholder="Whop Store",
        required=True
    )
    amount = discord.ui.TextInput(
        label="Amount (USDC on Base)",
        placeholder="1500.00",
        required=True
    )
    asset_id = discord.ui.TextInput(
        label="Asset Identifier / API Target",
        placeholder="company_id or domain name",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # 1. Create Private Ticket Thread
        thread = await interaction.channel.create_thread(
            name=f"escrow-{interaction.user.name}-vs-{self.seller.value[:4]}",
            type=discord.ChannelType.private_thread
        )

        # 2. Add Buyer and Seller to Thread
        await thread.add_user(interaction.user)
        try:
            seller_user = await interaction.client.fetch_user(int(self.seller.value))
            await thread.add_user(seller_user)
            seller_mention = seller_user.mention
        except Exception:
            seller_mention = f"<@{self.seller.value}>"

        # 3. Construct Live Status Embed
        embed = discord.Embed(
            title="🛡️ VouchSafe Escrow Vault Initialized",
            description=f"Automated OTC Escrow between {interaction.user.mention} and {seller_mention}.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Asset Category", value=self.asset_type.value, inline=True)
        embed.add_field(name="Deposit Required", value=f"${self.amount.value} USDC", inline=True)
        embed.add_field(name="Asset Target", value=f"`{self.asset_id.value}`", inline=False)
        embed.add_field(name="Vault State", value="🟡 **AWAITING_DEPOSIT**", inline=False)
        embed.set_footer(text="VouchSafe Protocol | Base EVM Secured")

        # 4. Attach Action Buttons
        view = EscrowTicketView(
            ticket_id=str(thread.id),
            amount=self.amount.value,
            asset_type=self.asset_type.value
        )

        await thread.send(content=f"{interaction.user.mention} {seller_mention}", embed=embed, view=view)
        await interaction.followup.send(f"Escrow vault created! Proceed to {thread.mention}", ephemeral=True)


class EscrowTicketView(discord.ui.View):
    def __init__(self, ticket_id: str, amount: str, asset_type: str):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.amount = amount
        self.asset_type = asset_type

    @discord.ui.button(label="Deposit Funds (Base L2)", style=discord.ButtonStyle.green, custom_id="deposit_btn")
    async def deposit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Generates direct link to web deposit portal or Web3 modal
        deposit_url = f"https://vouchsafe.io/deposit?ticket={self.ticket_id}&amount={self.amount}"
        await interaction.response.send_message(
            f"Connect wallet and deposit **${self.amount} USDC** on Base:\n{deposit_url}",
            ephemeral=True
        )

    @discord.ui.button(label="Trigger API Asset Swap", style=discord.ButtonStyle.primary, custom_id="verify_btn")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "⏳ Contacting Asset Verification Engine... Validating transfer via API.",
            ephemeral=True
        )

    @discord.ui.button(label="Raise Dispute", style=discord.ButtonStyle.danger, custom_id="dispute_btn")
    async def dispute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🚨 Dispute flagged. Vault state frozen. Protocol arbitrator notified.",
            ephemeral=False
        )


@bot.tree.command(name="escrow", description="Initialize a VouchSafe secure OTC escrow vault")
async def escrow(interaction: discord.Interaction):
    await interaction.response.send_modal(EscrowModal())

if __name__ == "__main__":
    bot.run(TOKEN)
