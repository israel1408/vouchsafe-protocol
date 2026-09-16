import os
import asyncio
import aiohttp
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

BASE_RPC_URL = os.getenv("BASE_RPC_URL")
FACTORY_ADDRESS = os.getenv("FACTORY_CONTRACT_ADDRESS")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))

# Event Signature Hashes (Keccak-256)
VAULT_FUNDED_TOPIC = w3.keccak(text="VaultFunded(uint256)").hex()
VAULT_RELEASED_TOPIC = w3.keccak(text="VaultReleased(uint256,uint256,uint256)").hex()

# Minimal ABI for checking Vault state
VAULT_ABI = [
    {
        "anonymous": False,
        "inputs": [{"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"}],
        "name": "VaultFunded",
        "type": "event"
    }
]

async def update_discord_thread_embed(channel_id: str, message_id: str, new_state: str, color_code: int):
    """Updates the Discord ticket embed state when blockchain events occur."""
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    # Fetch original message payload to preserve fields
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return
            msg_data = await resp.json()

        if not msg_data.get("embeds"):
            return

        embed = msg_data["embeds"][0]
        embed["color"] = color_code

        # Update Vault State field
        for field in embed.get("fields", []):
            if field["name"] == "Vault State":
                field["value"] = new_state

        patch_payload = {"embeds": [embed]}
        async with session.patch(url, headers=headers, json=patch_payload) as patch_resp:
            if patch_resp.status == 200:
                print(f"Updated Discord Message [{message_id}] -> {new_state}")


async def monitor_base_events(poll_interval: int = 3):
    """Polls Base L2 logs for Vault deposit and settlement events."""
    print("🎧 VouchSafe Web3 Listener running... Monitoring Base L2 events.")
    latest_block = w3.eth.block_number

    while True:
        try:
            current_block = w3.eth.block_number
            if current_block > latest_block:
                # Fetch log events across recent blocks
                filter_params = {
                    "fromBlock": latest_block + 1,
                    "toBlock": current_block,
                    "topics": [[VAULT_FUNDED_TOPIC, VAULT_RELEASED_TOPIC]]
                }
                logs = w3.eth.get_logs(filter_params)

                for log in logs:
                    topic_hex = log["topics"][0].hex()
                    vault_address = log["address"]

                    if topic_hex == VAULT_FUNDED_TOPIC:
                        print(f"💰 Vault Funded Detected on Base: {vault_address}")
                        # Event trigger hook: Notify Discord ticket thread
                        # (Mapped via database ticket_id lookup for vault_address)

                    elif topic_hex == VAULT_RELEASED_TOPIC:
                        print(f"🚀 Vault Payout Released on Base: {vault_address}")

                latest_block = current_block

        except Exception as e:
            print(f"Listener Error: {e}")

        await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    asyncio.run(monitor_base_events())
