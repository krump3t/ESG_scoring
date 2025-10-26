"""
Data providers for ESG report ingestion

Each provider implements a common interface for accessing verified public data sources.
"""

import logging

from .base_provider import BaseDataProvider

logger = logging.getLogger(__name__)

# Optional imports (may fail if dependencies not installed)
__all__ = ['BaseDataProvider']

try:
    from .cdp_provider import CDPClimateProvider
    __all__.append('CDPClimateProvider')
except ImportError as e:
    logger.warning(f"CDPClimateProvider not available: {e}")

try:
    from .sec_edgar_provider import SECEdgarProvider
    __all__.append('SECEdgarProvider')
except ImportError as e:
    logger.warning(f"SECEdgarProvider not available: {e}")
