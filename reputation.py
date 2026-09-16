import logging

logger = logging.getLogger("vouchsafe.reputation")

async def calculate_vouch_score(user_id: int, rating: int) -> float:
    """
    Calculates an updated VouchScore rating for a user on a 0.0 to 100.0 scale.
    Ratings range from 1 to 5 stars, adjusting score delta based on performance.
    """
    base_score = 100.0
    
    # Rating impact mapping (1 star = -5.0, 3 stars = 0.0, 5 stars = +5.0)
    rating_delta = (rating - 3) * 2.5
    
    # Compute new score clamped strictly between 0.0 and 100.0
    new_score = max(0.0, min(100.0, base_score + rating_delta))
    logger.info(f"User {user_id} VouchScore updated: {new_score:.1f} (Rating input: {rating})")
    return new_score


def get_reputation_tier(vouch_score: float, volume_usdc: float = 0.0) -> str:
    """Determines user's role tier based on VouchScore and volume metrics."""
    if vouch_score >= 90.0 and volume_usdc >= 50000.0:
        return "Tier 3: Apex Trader"
    elif vouch_score >= 70.0 and volume_usdc >= 10000.0:
        return "Tier 2: Trusted Trader"
    else:
        return "Tier 1: Novice Trader"
