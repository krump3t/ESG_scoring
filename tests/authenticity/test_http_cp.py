"""Test suite for http_client.py — HTTP client abstraction for testability.

TDD-First: Tests define the contract for socket-free HTTP operations.
Validates that fixture-based mocking prevents live network calls in tests.
"""

import pytest
from typing import Dict, Any
from hypothesis import given, settings, strategies as st


@pytest.mark.cp
class TestHTTPClientCP:
    """Critical path tests for HTTP abstraction."""

    def test_http_client_abc_has_get_method(self):
        """Verify HTTPClient ABC defines get() method."""
        from libs.utils.http_client import HTTPClient

        assert hasattr(HTTPClient, 'get')

    def test_http_client_abc_has_post_method(self):
        """Verify HTTPClient ABC defines post() method."""
        from libs.utils.http_client import HTTPClient

        assert hasattr(HTTPClient, 'post')

    def test_mock_http_client_returns_fixture_response(self):
        """Verify MockHTTPClient returns fixture-based responses."""
        from libs.utils.http_client import MockHTTPClient

        client = MockHTTPClient(fixtures={
            "https://api.example.com/data": {"status": 200, "data": {"key": "value"}}
        })
        response = client.get("https://api.example.com/data")

        assert response.status_code == 200
        assert response.json() == {"key": "value"}

    def test_mock_http_client_handles_missing_fixture(self):
        """Failure path: MockHTTPClient gracefully handles missing URLs."""
        from libs.utils.http_client import MockHTTPClient

        client = MockHTTPClient(fixtures={})

        # Should raise KeyError or return 404
        try:
            response = client.get("https://api.example.com/unknown")
            assert response.status_code == 404
        except KeyError:
            # Also acceptable
            pass

    def test_mock_http_client_post_with_json_data(self):
        """Verify MockHTTPClient.post() works with JSON payloads."""
        from libs.utils.http_client import MockHTTPClient

        client = MockHTTPClient(fixtures={
            "https://api.example.com/submit": {"status": 201, "data": {"id": "123"}}
        })
        response = client.post(
            "https://api.example.com/submit",
            json={"name": "test"}
        )

        assert response.status_code == 201
        assert response.json()["id"] == "123"

    def test_real_http_client_singleton(self):
        """Verify RealHTTPClient can be instantiated."""
        from libs.utils.http_client import RealHTTPClient

        client = RealHTTPClient()
        assert client is not None

    def test_http_client_dependency_injection(self):
        """Verify HTTP client can be injected for testing."""
        from libs.utils.http_client import MockHTTPClient

        fixtures = {
            "https://api.test.com/users": {
                "status": 200,
                "data": [{"id": 1, "name": "Alice"}]
            }
        }
        client = MockHTTPClient(fixtures=fixtures)

        # Can be passed as dependency
        response = client.get("https://api.test.com/users")
        assert response.status_code == 200

    def test_mock_http_client_fixtures_dictionary_structure(self):
        """Verify fixtures follow standard structure: URL -> response dict."""
        from libs.utils.http_client import MockHTTPClient

        fixtures: Dict[str, Dict[str, Any]] = {
            "https://api.example.com/endpoint1": {
                "status": 200,
                "data": {"result": "success"}
            },
            "https://api.example.com/endpoint2": {
                "status": 404,
                "data": {"error": "not found"}
            }
        }
        client = MockHTTPClient(fixtures=fixtures)

        response1 = client.get("https://api.example.com/endpoint1")
        response2 = client.get("https://api.example.com/endpoint2")

        assert response1.status_code == 200
        assert response2.status_code == 404

    @given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10))
    @settings(max_examples=5)
    def test_mock_http_client_accepts_any_fixture_key(self, key_suffix: str):
        """Property test: MockHTTPClient accepts various URL patterns."""
        from libs.utils.http_client import MockHTTPClient

        url = f"https://api.example.com/{key_suffix}"
        fixtures = {url: {"status": 200, "data": {}}}
        client = MockHTTPClient(fixtures=fixtures)

        response = client.get(url)
        assert response.status_code == 200

    def test_http_client_no_live_network_calls_in_tests(self):
        """Integration: Verify MockHTTPClient prevents live HTTP calls."""
        from libs.utils.http_client import MockHTTPClient

        # Use only local fixtures
        fixtures = {
            "https://api.example.com/safe": {"status": 200, "data": "safe"}
        }
        client = MockHTTPClient(fixtures=fixtures)

        # Should not attempt to connect to actual network
        response = client.get("https://api.example.com/safe")
        assert response.status_code == 200

    def test_http_response_object_has_status_code(self):
        """Verify HTTP response objects provide status_code attribute."""
        from libs.utils.http_client import MockHTTPClient

        client = MockHTTPClient(fixtures={
            "https://api.test.com": {"status": 200}
        })
        response = client.get("https://api.test.com")

        assert hasattr(response, 'status_code')
        assert response.status_code == 200

    def test_http_response_object_has_json_method(self):
        """Verify HTTP response objects provide json() method."""
        from libs.utils.http_client import MockHTTPClient

        client = MockHTTPClient(fixtures={
            "https://api.test.com": {"status": 200, "data": {"key": "val"}}
        })
        response = client.get("https://api.test.com")

        assert hasattr(response, 'json')
        assert callable(response.json)
        assert response.json() == {"key": "val"}

    def test_mock_http_client_post_failure_missing_url(self):
        """Failure path: POST to missing URL raises KeyError."""
        from libs.utils.http_client import MockHTTPClient

        client = MockHTTPClient(fixtures={})

        with pytest.raises(KeyError):
            client.post("https://api.example.com/missing", json={"data": "test"})

    def test_http_response_with_empty_data(self):
        """Verify HTTP response with no data field returns empty dict."""
        from libs.utils.http_client import MockHTTPClient

        client = MockHTTPClient(fixtures={
            "https://api.test.com": {"status": 204}
        })
        response = client.get("https://api.test.com")

        assert response.status_code == 204
        # When no data field, implementation returns empty dict
        assert response.json() == {}
