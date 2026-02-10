"""
Crypto Episode Count Criterion - Deterministic

Counts the number of crypto/web3 related episodes in the top N recommendations.
Used to verify category personalization for crypto-focused users.
"""

from typing import Any, Dict, List


DEFAULT_KEYWORDS = [
    "crypto", "bitcoin", "ethereum", "web3", "blockchain", 
    "defi", "btc", "eth", "stablecoin", "nft", "token",
    "bankless", "unchained", "coinbase", "binance"
]


def compute_crypto_count(response: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Count crypto/web3 episodes in top N recommendations.
    
    Args:
        response: API response with episodes list
        params: {
            "top_n": Number of episodes to consider (default 10),
            "threshold": Minimum crypto episodes to pass (default 5),
            "keywords": List of crypto keywords to match
        }
    
    Returns:
        {
            "score": int (count of crypto episodes),
            "passed": bool,
            "details": str,
            "matched_episodes": list of episode titles that matched
        }
    """
    top_n = params.get("top_n", 10)
    threshold = params.get("threshold", 5)
    keywords = [k.lower() for k in params.get("keywords", DEFAULT_KEYWORDS)]
    
    episodes = response.get("episodes", [])[:top_n]
    
    if not episodes:
        return {
            "score": 0,
            "passed": False,
            "details": "No episodes returned",
            "matched_episodes": []
        }
    
    # Count crypto episodes
    crypto_count = 0
    matched_episodes = []
    
    for ep in episodes:
        if is_crypto_episode(ep, keywords):
            crypto_count += 1
            matched_episodes.append(ep.get("title", "Unknown"))
    
    return {
        "score": crypto_count,
        "passed": crypto_count >= threshold,
        "details": f"crypto_count={crypto_count}/{top_n} (threshold={threshold})",
        "matched_episodes": matched_episodes
    }


def is_crypto_episode(episode: Dict[str, Any], keywords: List[str]) -> bool:
    """
    Check if an episode is crypto/web3 related.
    
    Checks:
    - Title
    - Key insight
    - Series name
    - Tags/categories
    """
    # Build searchable text
    title = episode.get("title", "").lower()
    key_insight = (episode.get("key_insight") or "").lower()
    series_name = episode.get("series", {}).get("name", "").lower()
    
    # Combine all text fields
    searchable = f"{title} {key_insight} {series_name}"
    
    # Check for keyword matches
    for keyword in keywords:
        if keyword in searchable:
            return True
    
    return False
