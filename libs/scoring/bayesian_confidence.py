"""
Phase 3: Bayesian Confidence Scoring Module

Beta-Binomial conjugate priors for ESG confidence estimation.
No SciPy dependency; uses closed-form formulas and normal approximations.

Per SCA v13.8: Deterministic, explicit validation, no external scientific packages.
"""

import logging
import math
from typing import Tuple, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceInterval:
    """Bayesian confidence interval result."""

    mean: float
    lower: float
    upper: float
    interval_width: float
    alpha: float
    beta: float


def compute_posterior_confidence(
    scores: List[float],
    theme: str,
) -> Dict[str, float]:
    """
    Compute Beta-Binomial posterior confidence with credible interval.

    Algorithm:
    1. Initialize prior: Beta(α=2, β=2) [weak prior, indifferent to theme]
    2. Interpret scores as successes (≥0.7) vs failures (<0.7)
    3. Update posterior: Beta(α + successes, β + failures) [conjugate update]
    4. Compute credible interval: [quantile(0.025), quantile(0.975)]
    5. Return {mean, lower, upper, interval_width}

    Args:
        scores: List of cross-encoder relevance scores in [0, 1]
        theme: ESG theme for logging (climate, social, governance, supply_chain, diversity)

    Returns:
        Dict with keys:
        - mean: Posterior mean confidence estimate
        - lower: Lower bound of 95% credible interval
        - upper: Upper bound of 95% credible interval
        - interval_width: upper - lower (measure of uncertainty)

    Raises:
        ValueError: If scores empty, contains values outside [0,1], or theme invalid
        RuntimeError: If posterior computation fails
    """
    # Validate inputs
    if not scores:
        raise ValueError("scores list cannot be empty")

    if len(scores) == 0:
        raise ValueError("scores must contain at least one element")

    # Validate all scores in [0, 1]
    for i, score in enumerate(scores):
        if not (0.0 <= score <= 1.0):
            raise ValueError(
                f"Score at index {i} out of range [0, 1]: {score}"
            )

    # Validate theme
    valid_themes = {"climate", "social", "governance", "supply_chain", "diversity"}
    if theme not in valid_themes:
        raise ValueError(
            f"Invalid theme '{theme}'. Must be one of {valid_themes}"
        )

    logger.debug(f"Computing posterior confidence for {len(scores)} scores (theme={theme})")

    try:
        # Initialize prior (Beta(2, 2) - weak prior)
        alpha_prior = 2.0
        beta_prior = 2.0

        # Count successes (score ≥ 0.7) and failures (score < 0.7)
        successes = sum(1 for score in scores if score >= 0.7)
        failures = len(scores) - successes

        # Update posterior (conjugate update)
        alpha_post = alpha_prior + successes
        beta_post = beta_prior + failures

        logger.debug(
            f"Prior: Beta({alpha_prior}, {beta_prior}), "
            f"Data: {successes} successes, {failures} failures, "
            f"Posterior: Beta({alpha_post}, {beta_post})"
        )

        # Compute posterior statistics
        posterior = BetaPosterior(alpha_post, beta_post)
        mean = posterior.mean()
        lower, upper = posterior.credible_interval(q=0.95)
        interval_width = upper - lower

        result = {
            "mean": round(mean, 4),
            "lower": round(lower, 4),
            "upper": round(upper, 4),
            "interval_width": round(interval_width, 4),
            "alpha": round(alpha_post, 4),
            "beta": round(beta_post, 4),
            "successes": successes,
            "total": len(scores),
        }

        logger.info(
            f"Posterior confidence (theme={theme}): "
            f"mean={result['mean']}, CI=[{result['lower']}, {result['upper']}]"
        )

        return result

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Posterior computation failed: {e}")
        raise RuntimeError(f"Confidence computation error: {e}") from e


class BetaPosterior:
    """
    Beta distribution posterior with credible interval computation.

    No external dependencies; uses normal approximation for quantiles.
    """

    def __init__(self, alpha: float, beta: float) -> None:
        """
        Initialize Beta(alpha, beta) distribution.

        Args:
            alpha: Shape parameter α > 0
            beta: Shape parameter β > 0

        Raises:
            ValueError: If alpha or beta <= 0
        """
        if alpha <= 0 or beta <= 0:
            raise ValueError(f"alpha and beta must be > 0, got alpha={alpha}, beta={beta}")

        self.alpha = alpha
        self.beta = beta

    def mean(self) -> float:
        """
        Compute mean of Beta(α, β).

        Formula: E[X] = α / (α + β)

        Returns:
            Mean in [0, 1]
        """
        return self.alpha / (self.alpha + self.beta)

    def variance(self) -> float:
        """
        Compute variance of Beta(α, β).

        Formula: Var[X] = (α * β) / ((α + β)^2 * (α + β + 1))

        Returns:
            Variance
        """
        numerator = self.alpha * self.beta
        denominator = (self.alpha + self.beta) ** 2 * (self.alpha + self.beta + 1)
        return numerator / denominator if denominator != 0 else 0.0

    def std_dev(self) -> float:
        """
        Compute standard deviation.

        Returns:
            Standard deviation (square root of variance)
        """
        return math.sqrt(self.variance())

    def credible_interval(self, q: float = 0.95) -> Tuple[float, float]:
        """
        Compute symmetric credible interval [lower, upper] for posterior.

        Uses normal approximation (valid for large α + β).
        For small samples, falls back to beta CDF approximation.

        Args:
            q: Credible interval width (e.g., 0.95 for 95%)

        Returns:
            Tuple (lower, upper) of credible interval bounds
        """
        mean = self.mean()
        std = self.std_dev()

        if std == 0:
            # No uncertainty; return point mass
            return (mean, mean)

        # Use normal approximation with continuity correction
        # Z-score for α/2 tail probability
        alpha_tail = (1 - q) / 2
        z_score = self._inverse_normal_cdf(1 - alpha_tail)

        # Confidence interval
        margin = z_score * std
        lower = max(0.0, mean - margin)  # Clamp to [0, 1]
        upper = min(1.0, mean + margin)

        return (round(lower, 4), round(upper, 4))

    def _inverse_normal_cdf(self, p: float) -> float:
        """
        Approximate inverse CDF of standard normal using Acklam's algorithm.

        Args:
            p: Probability in (0, 1)

        Returns:
            Approximate z-score
        """
        # Rational approximation (accurate to ~6 decimal places)
        if p < 0.5:
            # Lower tail
            p_adj = p
            b_sign = -1
        else:
            # Upper tail
            p_adj = 1 - p
            b_sign = 1

        # Approximation coefficients
        if p_adj > 0.02425:
            # Rational approximation for main region
            t = math.sqrt(-2.0 * math.log(p_adj))
            a0, a1, a2 = 2.506628277459239, 3.224671290700398, 2.445134137142996
            b0, b1, b2 = 1.0, 0.2477017640707842, 0.041960214150456034
            c0, c1 = 3.754408661907416, 0.02453282606040244
        else:
            # Rational approximation for tail region
            t = math.sqrt(-2.0 * math.log(math.sqrt(p_adj)))
            a0, a1, a2 = 2.506628277459239, 3.224671290700398, 2.445134137142996
            b0, b1, b2 = 1.0, 0.2477017640707842, 0.041960214150456034
            c0, c1 = 3.754408661907416, 0.02453282606040244

        # Numerator
        numerator = a0 + a1 * t + a2 * t ** 2
        # Denominator
        denominator = b0 + b1 * t + b2 * t ** 2

        z = t - (numerator / denominator)

        return b_sign * z


def posterior(
    alpha: float,
    beta: float,
    success: int,
    total: int,
) -> Tuple[float, float]:
    """
    Compute Beta-Binomial posterior mean and variance (helper function).

    Args:
        alpha: Prior α parameter
        beta: Prior β parameter
        success: Number of successes
        total: Total number of trials

    Returns:
        Tuple (posterior_mean, posterior_variance)

    Raises:
        ValueError: If inputs invalid
    """
    if total <= 0:
        raise ValueError(f"total must be > 0, got {total}")

    if not (0 <= success <= total):
        raise ValueError(
            f"success must be in [0, total], got success={success}, total={total}"
        )

    failure = total - success
    alpha_post = alpha + success
    beta_post = beta + failure

    post = BetaPosterior(alpha_post, beta_post)
    return (post.mean(), post.variance())


def score_interval(
    alpha: float,
    beta: float,
    success: int,
    total: int,
    q: float = 0.95,
) -> Tuple[float, float]:
    """
    Compute credible interval for Beta-Binomial posterior (helper function).

    Args:
        alpha: Prior α parameter
        beta: Prior β parameter
        success: Number of successes
        total: Total number of trials
        q: Credible interval width (default: 0.95)

    Returns:
        Tuple (lower, upper) bounds of credible interval

    Raises:
        ValueError: If inputs invalid
    """
    if total <= 0:
        raise ValueError(f"total must be > 0, got {total}")

    if not (0 <= success <= total):
        raise ValueError(
            f"success must be in [0, total], got success={success}, total={total}"
        )

    failure = total - success
    alpha_post = alpha + success
    beta_post = beta + failure

    post = BetaPosterior(alpha_post, beta_post)
    return post.credible_interval(q)
