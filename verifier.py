import os
import aiohttp
import asyncio
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# Environment Credentials
WHOP_API_KEY = os.getenv("WHOP_API_KEY")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GITHUB_PAT_TOKEN = os.getenv("GITHUB_PAT_TOKEN")

BASE_RPC_URL = os.getenv("BASE_RPC_URL")
FACTORY_ADDRESS = os.getenv("FACTORY_CONTRACT_ADDRESS")
ORACLE_PRIVATE_KEY = os.getenv("ORACLE_PRIVATE_KEY")

w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))

FACTORY_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "ticketId", "type": "bytes32"}],
        "name": "triggerRelease",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

class AssetVerifier:

    @staticmethod
    async def verify_whop_ownership(company_id: str, expected_owner_id: str) -> bool:
        """Verifies if Whop company ownership has transferred to the buyer."""
        url = f"https://api.whop.com/api/v2/companies/{company_id}"
        headers = {
            "Authorization": f"Bearer {WHOP_API_KEY}",
            "Accept": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                return str(data.get("user_id")) == str(expected_owner_id)

    @staticmethod
    async def verify_domain_dns(domain_name: str, expected_txt_record: str) -> bool:
        """Verifies Cloudflare DNS TXT record challenge for domain transfers."""
        url = f"https://api.cloudflare.com/client/v4/zones?name={domain_name}"
        headers = {
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                results = data.get("result", [])
                if not results:
                    return False
                
                zone_id = results[0]["id"]
                dns_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=TXT"
                
                async with session.get(dns_url, headers=headers) as dns_resp:
                    if dns_resp.status != 200:
                        return False
                    dns_data = await dns_resp.json()
                    for record in dns_data.get("result", []):
                        if record.get("content") == expected_txt_record:
                            return True
        return False

    @staticmethod
    async def verify_discord_server_owner(guild_id: str, expected_owner_discord_id: str) -> bool:
        """Queries Discord REST API to check if primary Guild ownership moved to buyer."""
        url = f"https://discord.com/api/v10/guilds/{guild_id}"
        headers = {
            "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                return str(data.get("owner_id")) == str(expected_owner_discord_id)

    @staticmethod
    async def verify_github_repo_owner(repo_full_name: str, expected_github_user: str) -> bool:
        """Checks if repository owner or primary admin collaborator matches buyer's GitHub handle."""
        # repo_full_name format: "org-or-user/repository-name"
        url = f"https://api.github.com/repos/{repo_full_name}"
        headers = {
            "Authorization": f"Bearer {GITHUB_PAT_TOKEN}",
            "Accept": "application/vnd.github+json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                
                # Direct repository owner check
                owner_login = data.get("owner", {}).get("login", "").lower()
                if owner_login == expected_github_user.lower():
                    return True
                
                # Fallback: Check if buyer was granted explicit Admin collaborator status
                collab_url = f"https://api.github.com/repos/{repo_full_name}/collaborators/{expected_github_user}/permission"
                async with session.get(collab_url, headers=headers) as collab_resp:
                    if collab_resp.status == 200:
                        collab_data = await collab_resp.json()
                        return collab_data.get("permission") == "admin"
        return False

    @staticmethod
    def trigger_onchain_payout(ticket_id_str: str) -> str:
        """Executes triggerRelease on EscrowVaultFactory smart contract via Oracle wallet."""
        account = w3.eth.account.from_key(ORACLE_PRIVATE_KEY)
        factory_contract = w3.eth.contract(address=FACTORY_ADDRESS, abi=FACTORY_ABI)
        ticket_bytes = w3.keccak(text=ticket_id_str)
        
        tx = factory_contract.functions.triggerRelease(ticket_bytes).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 180000,
            'maxFeePerGas': w3.to_wei('2', 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei('0.1', 'gwei')
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, ORACLE_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return w3.to_hex(tx_hash)

async def process_verification_job(ticket_id: str, asset_type: str, target_id: str, expected_value: str) -> bool:
    """Central Routing Engine for asset verification execution."""
    asset = asset_type.lower().strip()
    verified = False

    if asset in ["whop", "whop store"]:
        verified = await AssetVerifier.verify_whop_ownership(target_id, expected_value)
    elif asset in ["domain", "cloudflare"]:
        verified = await AssetVerifier.verify_domain_dns(target_id, expected_value)
    elif asset in ["discord", "discord server"]:
        verified = await AssetVerifier.verify_discord_server_owner(target_id, expected_value)
    elif asset in ["github", "github repo", "codebase"]:
        verified = await AssetVerifier.verify_github_repo_owner(target_id, expected_value)
    else:
        print(f"Unknown asset type: '{asset_type}'. Requires manual attestation.")
        return False

    if verified:
        print(f"✅ Asset verified for Ticket [{ticket_id}]. Triggering Base L2 Vault release...")
        tx_hash = AssetVerifier.trigger_onchain_payout(ticket_id)
        print(f"🚀 Settlement Complete! Base Tx Hash: {tx_hash}")
        return True
    else:
        print(f"⏳ Verification pending or failed for Ticket [{ticket_id}].")
        return False
