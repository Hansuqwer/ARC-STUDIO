"""Simple ELO rating system replacing Bradley-Terry MLE.

Avoids pandas/sklearn/numpy dependencies. Uses standard ELO formula:
    R_new = R_old + K * (S - E)
where:
    S = 1 for win, 0.5 for tie, 0 for loss
    E = 1 / (1 + 10^((R_opp - R_old) / 400))
"""

from typing import Any


def compute_elo(
    outcomes: list[dict[str, Any]],
    models: list[str] | None = None,
    k_factor: int = 32,
    initial_rating: float = 1500.0,
) -> dict[str, float]:
    """Compute ELO ratings from outcome records.

    Args:
        outcomes: List of outcome dicts with 'completionItems' and 'acceptedIndex'
        models: Optional list of models to include (None = all)
        k_factor: ELO K-factor (default 32)
        initial_rating: Starting rating for new models (default 1500)

    Returns:
        Dict mapping model name to ELO rating
    """
    ratings: dict[str, float] = {}

    # Initialize ratings for all models
    if models:
        for model in models:
            ratings[model] = initial_rating

    # Process each outcome
    for outcome in outcomes:
        items = outcome.get("completionItems", [])
        if len(items) != 2:
            continue

        model_a = items[0].get("model")
        model_b = items[1].get("model")
        accepted_index = outcome.get("acceptedIndex")

        if not model_a or not model_b:
            continue

        # Skip if model not in allowed list
        if models and (model_a not in models or model_b not in models):
            continue

        # Initialize ratings if needed
        if model_a not in ratings:
            ratings[model_a] = initial_rating
        if model_b not in ratings:
            ratings[model_b] = initial_rating

        # Determine scores (S)
        if accepted_index == 0:
            score_a, score_b = 1.0, 0.0  # A wins
        elif accepted_index == 1:
            score_a, score_b = 0.0, 1.0  # B wins
        else:
            score_a, score_b = 0.5, 0.5  # Tie

        # Calculate expected scores (E)
        rating_a, rating_b = ratings[model_a], ratings[model_b]
        expected_a = 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))
        expected_b = 1.0 / (1.0 + 10 ** ((rating_a - rating_b) / 400.0))

        # Update ratings
        ratings[model_a] = rating_a + k_factor * (score_a - expected_a)
        ratings[model_b] = rating_b + k_factor * (score_b - expected_b)

    return ratings


def get_leaderboard(
    outcomes: list[dict[str, Any]],
    models: list[str] | None = None,
    k_factor: int = 32,
) -> list[dict[str, Any]]:
    """Get sorted leaderboard with ELO ratings and vote counts.

    Args:
        outcomes: List of outcome records
        models: Optional list of models to include
        k_factor: ELO K-factor

    Returns:
        List of dicts with 'model', 'elo', 'votes', 'wins' sorted by ELO desc
    """
    ratings = compute_elo(outcomes, models, k_factor)

    # Count votes and wins per model
    stats: dict[str, dict[str, int]] = {}
    for outcome in outcomes:
        items = outcome.get("completionItems", [])
        if len(items) != 2:
            continue

        model_a = items[0].get("model")
        model_b = items[1].get("model")
        accepted_index = outcome.get("acceptedIndex")

        if not model_a or not model_b:
            continue
        if models and (model_a not in models or model_b not in models):
            continue

        # Initialize stats
        if model_a not in stats:
            stats[model_a] = {"votes": 0, "wins": 0}
        if model_b not in stats:
            stats[model_b] = {"votes": 0, "wins": 0}

        # Increment votes
        stats[model_a]["votes"] += 1
        stats[model_b]["votes"] += 1

        # Increment wins
        if accepted_index == 0:
            stats[model_a]["wins"] += 1
        elif accepted_index == 1:
            stats[model_b]["wins"] += 1

    # Build leaderboard
    leaderboard = []
    for model, rating in ratings.items():
        model_stats = stats.get(model, {"votes": 0, "wins": 0})
        leaderboard.append(
            {
                "model": model,
                "elo": round(rating, 2),
                "votes": model_stats["votes"],
                "wins": model_stats["wins"],
                "win_rate": (
                    round(model_stats["wins"] / model_stats["votes"], 3)
                    if model_stats["votes"] > 0
                    else 0.0
                ),
            }
        )

    # Sort by ELO descending
    leaderboard.sort(key=lambda x: x["elo"], reverse=True)
    return leaderboard
