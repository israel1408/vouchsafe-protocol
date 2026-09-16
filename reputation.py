import math
import time
from typing import Dict, Any

BASE_SCORE = 100
MAX_SCORE = 1000

class VouchScoreEngine:

    @staticmethod
    def calculate_score(
        total_volume_usdc: float,
        successful_trades: int,
        disputes_lost: int,
        account_age_days: int
    ) -> int:
        """
        Calculates a user's non-transferable VouchScore (100 - 1000 scale).
        Uses logarithmic scaling on volume to prevent manipulation via micro-transactions.
        """
        if successful_trades == 0:
            return BASE_SCORE

        # 1. Volume Factor (Max 350 pts)
        volume_score = min(350, math.log10(max(1, total_volume_usdc)) * 70)

        # 2. Trade Count Factor (Max 250 pts)
        trade_score = min(250, successful_trades * 15)

        # 3. Longevity Factor (Max 100 pts)
        longevity_score = min(100, account_age_days * 0.5)

        # 4. Dispute Penalty (High penalty for failed/fraudulent deals)
        dispute_penalty = disputes_lost * 200

        raw_score = BASE_SCORE + volume_score + trade_score + longevity_score - dispute_penalty
        return int(max(BASE_SCORE, min(MAX_SCORE, raw_score)))

    @staticmethod
    def get_tier(score: int) -> Dict[str, Any]:
        """Returns the reputation badge, fee discounts, and single-trade limits based on VouchScore."""
        if score >= 900:
            return {"tier": "Apex OTC Trader", "badge": "💎", "fee_discount_bps": 40, "max_single_trade": 100000}
        elif score >= 750:
            return {"tier": "Gold Merchant", "badge": "🥇", "fee_discount_bps": 20, "max_single_trade": 50000}
        elif score >= 500:
            return {"tier": "Verified Trader", "badge": "🥈", "fee_discount_bps": 10, "max_single_trade": 15000}
        elif score >= 250:
            return {"tier": "Established", "badge": "🥉", "fee_discount_bps": 0, "max_single_trade": 5000}
        else:
            return {"tier": "Unverified / New", "badge": "⚪", "fee_discount_bps": 0, "max_single_trade": 1000}

    @staticmethod
    def generate_reputation_embed_data(user_discord_id: str, score: int, total_vol: float, trades: int) -> Dict[str, Any]:
        """Formats VouchScore data into Discord-ready card fields."""
        tier_info = VouchScoreEngine.get_tier(score)
        return {
            "title": f"{tier_info['badge']} VouchScore Profile: <@{user_discord_id}>",
            "score": f"**{score}** / 1000",
            "tier": tier_info["tier"],
            "total_volume": f"${total_vol:,.2f} USDC",
            "completed_trades": trades,
            "max_trade_limit": f"${tier_info['max_single_trade']:,} USDC",
            "fee_discount": f"{tier_info['fee_discount_bps'] / 100}% discount"
        }
