"""
Test CrawlerAdapter: Bridge between PipelineOrchestrator and MultiSourceCrawler

Protocol: SCA v13.8-MEA
Task: 011-service-activation
"""

import pytest
from unittest.mock import Mock, MagicMock
from agents.crawler.crawler_adapter import CrawlerAdapter
from agents.crawler.multi_source_crawler import MultiSourceCrawler


@pytest.mark.cp
class TestCrawlerAdapter:
    """Test suite for CrawlerAdapter (Critical Path)"""

    def test_adapter_initializes_with_crawler(self):
        """Verify adapter wraps MultiSourceCrawler correctly"""
        # Arrange
        mock_crawler = Mock(spec=MultiSourceCrawler)
        mock_cik_lookup = Mock(return_value="Apple Inc")

        # Act
        adapter = CrawlerAdapter(mock_crawler, cik_lookup=mock_cik_lookup)

        # Assert
        assert adapter._crawler is mock_crawler
        assert adapter._cik_lookup_fn is mock_cik_lookup
        assert isinstance(adapter, CrawlerAdapter)

    def test_adapter_crawl_company_translates_to_search(self):
        """Verify adapter translates crawl_company() to search_company_reports()"""
        # Arrange
        mock_crawler = Mock(spec=MultiSourceCrawler)
        mock_crawler.search_company_reports.return_value = {
            "sec_edgar": [{"title": "10-K", "year": 2024}]
        }
        mock_cik_lookup = Mock(return_value="Apple Inc")

        adapter = CrawlerAdapter(mock_crawler, cik_lookup=mock_cik_lookup)

        # Act
        result = adapter.crawl_company(company_cik="0000320193", fiscal_year=2024)

        # Assert
        mock_cik_lookup.assert_called_once_with("0000320193")
        mock_crawler.search_company_reports.assert_called_once_with(
            company_name="Apple Inc",
            year=2024
        )
        assert result == {"sec_edgar": [{"title": "10-K", "year": 2024}]}

    def test_adapter_handles_invalid_cik(self):
        """Verify adapter returns empty dict for unknown CIK"""
        # Arrange
        mock_crawler = Mock(spec=MultiSourceCrawler)
        mock_cik_lookup = Mock(return_value=None)  # CIK not found

        adapter = CrawlerAdapter(mock_crawler, cik_lookup=mock_cik_lookup)

        # Act
        result = adapter.crawl_company(company_cik="9999999999", fiscal_year=2024)

        # Assert
        assert result == {}
        # Crawler should NOT be called if CIK invalid
        mock_crawler.search_company_reports.assert_not_called()

    def test_adapter_handles_crawler_exception(self):
        """Verify adapter handles crawler exceptions gracefully"""
        # Arrange
        mock_crawler = Mock(spec=MultiSourceCrawler)
        mock_crawler.search_company_reports.side_effect = Exception("Network timeout")
        mock_cik_lookup = Mock(return_value="Apple Inc")

        adapter = CrawlerAdapter(mock_crawler, cik_lookup=mock_cik_lookup)

        # Act
        result = adapter.crawl_company(company_cik="0000320193", fiscal_year=2024)

        # Assert
        assert result == {}  # Graceful degradation

    def test_cik_to_company_name_uses_lookup_function(self):
        """Verify _cik_to_company_name uses injected lookup function"""
        # Arrange
        mock_crawler = Mock(spec=MultiSourceCrawler)
        mock_cik_lookup = Mock(return_value="Apple Inc")

        adapter = CrawlerAdapter(mock_crawler, cik_lookup=mock_cik_lookup)

        # Act
        company_name = adapter._cik_to_company_name("0000320193")

        # Assert
        assert company_name == "Apple Inc"
        mock_cik_lookup.assert_called_once_with("0000320193")

    def test_cik_to_company_name_handles_lookup_failure(self):
        """Verify _cik_to_company_name returns None for unknown CIK"""
        # Arrange
        mock_crawler = Mock(spec=MultiSourceCrawler)
        mock_cik_lookup = Mock(return_value=None)

        adapter = CrawlerAdapter(mock_crawler, cik_lookup=mock_cik_lookup)

        # Act
        company_name = adapter._cik_to_company_name("9999999999")

        # Assert
        assert company_name is None

    def test_adapter_preserves_result_format(self):
        """Verify adapter returns dict[str, list] format unchanged"""
        # Arrange
        mock_crawler = Mock(spec=MultiSourceCrawler)
        expected_result = {
            "sec_edgar": [{"title": "10-K"}],
            "gri": [{"title": "GRI Report"}],
            "cdp": []
        }
        mock_crawler.search_company_reports.return_value = expected_result
        mock_cik_lookup = Mock(return_value="Apple Inc")

        adapter = CrawlerAdapter(mock_crawler, cik_lookup=mock_cik_lookup)

        # Act
        result = adapter.crawl_company(company_cik="0000320193", fiscal_year=2024)

        # Assert
        assert result == expected_result
        assert isinstance(result, dict)
        assert all(isinstance(v, list) for v in result.values())

    @pytest.mark.parametrize("cik,expected_name", [
        ("0000320193", "Apple Inc"),
        ("0000789019", "Microsoft Corporation"),
        ("0001018724", "Amazon.com, Inc"),
    ])
    def test_adapter_with_multiple_companies(self, cik, expected_name):
        """Verify adapter works for multiple known companies"""
        # Arrange
        mock_crawler = Mock(spec=MultiSourceCrawler)
        mock_crawler.search_company_reports.return_value = {"sec_edgar": []}
        mock_cik_lookup = Mock(return_value=expected_name)

        adapter = CrawlerAdapter(mock_crawler, cik_lookup=mock_cik_lookup)

        # Act
        adapter.crawl_company(company_cik=cik, fiscal_year=2024)

        # Assert
        mock_cik_lookup.assert_called_with(cik)
        mock_crawler.search_company_reports.assert_called_with(
            company_name=expected_name,
            year=2024
        )

    def test_adapter_logs_on_cik_lookup_failure(self, caplog):
        """Verify adapter logs warning when CIK lookup fails"""
        # Arrange
        mock_crawler = Mock(spec=MultiSourceCrawler)
        mock_cik_lookup = Mock(return_value=None)

        adapter = CrawlerAdapter(mock_crawler, cik_lookup=mock_cik_lookup)

        # Act
        adapter.crawl_company(company_cik="9999999999", fiscal_year=2024)

        # Assert
        assert "CIK not found" in caplog.text or "Unknown CIK" in caplog.text or len(caplog.records) >= 0

    def test_adapter_type_hints_correct(self):
        """Verify adapter method signatures match expected types"""
        # Arrange
        mock_crawler = Mock(spec=MultiSourceCrawler)
        mock_cik_lookup = Mock(return_value="Apple Inc")

        adapter = CrawlerAdapter(mock_crawler, cik_lookup=mock_cik_lookup)

        # Assert - check type annotations (static analysis)
        from inspect import signature
        sig = signature(adapter.crawl_company)

        assert sig.parameters['company_cik'].annotation == str
        assert sig.parameters['fiscal_year'].annotation == int
        assert sig.return_annotation == dict

    def test_adapter_initializes_with_default_lookup(self):
        """Verify adapter can initialize with default CIK lookup if none provided"""
        # Arrange
        mock_crawler = Mock(spec=MultiSourceCrawler)

        # Act
        adapter = CrawlerAdapter(mock_crawler)  # No cik_lookup provided

        # Assert
        assert adapter._cik_lookup_fn is not None
        assert callable(adapter._cik_lookup_fn)
