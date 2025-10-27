"""HTTP client abstraction for testability and determinism.

Provides HTTPClient ABC with RealHTTPClient (production) and MockHTTPClient (testing).
Enables fixture-based mocking to prevent live HTTP calls in tests.

Usage:
    from libs.utils.http_client import HTTPClient, MockHTTPClient, RealHTTPClient

    # Production: real HTTP calls
    client: HTTPClient = RealHTTPClient()
    response = client.get("https://api.example.com/data")

    # Testing: fixture-based mocking (zero network)
    fixtures = {
        "https://api.example.com/data": {"status": 200, "data": {...}}
    }
    client: HTTPClient = MockHTTPClient(fixtures=fixtures)
    response = client.get("https://api.example.com/data")
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class HTTPResponse:
    """Mock HTTP response object for fixture-based testing."""

    def __init__(self, status_code: int, data: Any = None):
        """Initialize HTTP response.

        Args:
            status_code: HTTP status code (200, 404, etc.)
            data: Response body data (dict for JSON responses)
        """
        self.status_code = status_code
        self._data = data

    def json(self) -> Any:
        """Return response body as parsed JSON.

        Returns:
            Deserialized JSON response data
        """
        return self._data


class HTTPClient(ABC):
    """Abstract base class for HTTP client operations."""

    @abstractmethod
    def get(self, url: str, **kwargs: Any) -> HTTPResponse:
        """Perform HTTP GET request.

        Args:
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            HTTPResponse object with status_code and json() method
        """
        pass

    @abstractmethod
    def post(self, url: str, **kwargs: Any) -> HTTPResponse:
        """Perform HTTP POST request.

        Args:
            url: Request URL
            **kwargs: Additional request parameters (e.g., json={...})

        Returns:
            HTTPResponse object with status_code and json() method
        """
        pass


class RealHTTPClient(HTTPClient):
    """Production HTTP client using requests library."""

    def __init__(self):
        """Initialize real HTTP client."""
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise ImportError(
                "requests library required for RealHTTPClient. "
                "Install with: pip install requests"
            )

    def get(self, url: str, **kwargs: Any) -> Any:
        """Perform real HTTP GET request.

        Args:
            url: Request URL
            **kwargs: Additional parameters for requests.get()

        Returns:
            requests.Response object
        """
        return self.requests.get(url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Any:
        """Perform real HTTP POST request.

        Args:
            url: Request URL
            **kwargs: Additional parameters for requests.post()

        Returns:
            requests.Response object
        """
        return self.requests.post(url, **kwargs)


class MockHTTPClient(HTTPClient):
    """Test HTTP client using fixture-based responses (zero network)."""

    def __init__(self, fixtures: Optional[Dict[str, Dict[str, Any]]] = None):
        """Initialize mock HTTP client with fixture responses.

        Args:
            fixtures: Dictionary mapping URLs to response dicts.
                     Response dict format: {"status": 200, "data": {...}}
        """
        self.fixtures = fixtures or {}

    def get(self, url: str, **kwargs: Any) -> HTTPResponse:
        """Perform mock HTTP GET request using fixtures.

        Args:
            url: Request URL (must match fixture key)
            **kwargs: Ignored (for API compatibility)

        Returns:
            HTTPResponse object with fixture data

        Raises:
            KeyError: If URL not found in fixtures
        """
        if url not in self.fixtures:
            raise KeyError(f"No fixture for URL: {url}")

        fixture = self.fixtures[url]
        status = fixture.get("status", 200)
        data = fixture.get("data", fixture.get("response_body", {}))

        return HTTPResponse(status_code=status, data=data)

    def post(self, url: str, **kwargs: Any) -> HTTPResponse:
        """Perform mock HTTP POST request using fixtures.

        Args:
            url: Request URL (must match fixture key)
            json: POST body (ignored; fixture response used)
            **kwargs: Ignored (for API compatibility)

        Returns:
            HTTPResponse object with fixture data

        Raises:
            KeyError: If URL not found in fixtures
        """
        if url not in self.fixtures:
            raise KeyError(f"No fixture for URL: {url}")

        fixture = self.fixtures[url]
        status = fixture.get("status", 201)
        data = fixture.get("data", fixture.get("response_body", {}))

        return HTTPResponse(status_code=status, data=data)
