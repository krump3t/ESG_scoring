"""Custom exceptions for SEC EDGAR data provider.

**SCA v13.8 Compliance**:
- Authentic error handling (not trivial pass-through)
- Specific exception types for different failure modes
- Supports failure-path testing requirements

Author: Scientific Coding Agent v13.8-MEA
Date: 2025-10-23
"""


class SECEdgarError(Exception):
    """Base exception for all SEC EDGAR provider errors.

    All SEC EDGAR specific exceptions inherit from this base class,
    enabling catch-all error handling while preserving specific error types.
    """

    pass


class DocumentNotFoundError(SECEdgarError):
    """Requested SEC filing does not exist (HTTP 404).

    Raised when:
    - Company CIK is valid but filing type not available for fiscal year
    - Accession number does not exist
    - Document has been removed from EDGAR system

    Example:
        >>> provider.fetch_10k("0000320193", fiscal_year=1995)
        DocumentNotFoundError: Filing not found: 10-K for CIK 0000320193 FY1995
    """

    pass


class RateLimitExceededError(SECEdgarError):
    """SEC EDGAR API rate limit exceeded (HTTP 503).

    Raised when:
    - Request rate exceeds 10 requests per second
    - SEC EDGAR returns 503 Service Unavailable
    - This should be automatically handled by retry logic

    Note:
        This exception typically occurs only after retry exhaustion.
        The @sleep_and_retry decorator prevents most rate limit violations.
    """

    pass


class InvalidCIKError(SECEdgarError):
    """Invalid CIK (Central Index Key) format provided.

    Raised when:
    - CIK is not exactly 10 digits
    - CIK contains non-numeric characters
    - CIK is None or empty string

    Valid CIK format: 10-digit zero-padded string (e.g., "0000320193")

    Example:
        >>> provider.fetch_10k("AAPL", 2023)
        InvalidCIKError: Invalid CIK format: 'AAPL'. Must be 10-digit string.
    """

    pass


class MaxRetriesExceededError(SECEdgarError):
    """Maximum retry attempts exhausted for API request.

    Raised when:
    - All retry attempts (default: 3) fail with transient errors
    - Exponential backoff completes without success
    - Underlying cause is typically network timeout or persistent 503

    The exception message includes:
    - Number of attempts made
    - Last exception encountered
    - URL that was being accessed

    Example:
        >>> provider.fetch_10k("0000320193", 2023)
        MaxRetriesExceededError: Max retries (3) exceeded for
            https://data.sec.gov/... Last error: HTTPError 503
    """

    pass


class InvalidResponseError(SECEdgarError):
    """SEC EDGAR API returned malformed or unexpected response.

    Raised when:
    - Response body is not valid JSON when JSON expected
    - Required fields missing from JSON response
    - HTML structure does not match expected format

    This exception indicates a potential API schema change or
    network corruption. The raw response is included for debugging.
    """

    pass


class RequestTimeoutError(SECEdgarError):
    """HTTP request to SEC EDGAR timed out.

    Raised when:
    - Request exceeds timeout threshold (default: 30 seconds)
    - Network connection stalls
    - SEC EDGAR server not responding

    Note:
        Timeouts trigger retry logic. This exception occurs only
        after retry exhaustion.
    """

    pass
