"""
Average Credibility Criterion - Deterministic

Computes the average credibility score of the top N recommended episodes.
This is a core quality metric that ensures recommendations meet a minimum
credibility standard.
"""

from typing import Any, Dict


def compute_avg_credibility(response: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute average credibility of top N episodes.
    
    Args:
        response: API response with episodes list
        params: {
            "top_n": Number of episodes to consider (default 10),
            "threshold": Pass threshold (default 3.0)
        }
    
    Returns:
        {
            "score": float (0-5),
            "passed": bool,
            "details": str
        }
    """
    top_n = params.get("top_n", 10)
    threshold = params.get("threshold", 3.0)
    
    episodes = response.get("episodes", [])[:top_n]
    
    if not episodes:
        return {
            "score": 0.0,
            "passed": False,
            "details": "No episodes returned"
        }
    
    # Extract credibility scores
    credibilities = []
    for ep in episodes:
        scores = ep.get("scores", {})
        cred = scores.get("credibility", 0)
        credibilities.append(cred)
    
    avg = sum(credibilities) / len(credibilities)
    
    return {
        "score": round(avg, 2),
        "passed": avg >= threshold,
        "details": f"avg_credibility={avg:.2f} (n={len(episodes)}, threshold={threshold})"
    }
