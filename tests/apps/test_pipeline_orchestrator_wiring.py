"""
Test PipelineOrchestrator Crawler Wiring: Task 011

Protocol: SCA v13.8-MEA
Task: 011-service-activation

Verifies orchestrator initializes crawler correctly with CrawlerAdapter.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from apps.pipeline_orchestrator import PipelineOrchestrator
from agents.crawler.crawler_adapter import CrawlerAdapter


@pytest.mark.cp
class TestPipelineOrchestratorWiring:
    """Test suite for orchestrator crawler initialization (Critical Path)"""

    @pytest.fixture
    def mock_config(self):
        """Standard configuration for orchestrator tests"""
        return {
            "paths": {
                "data_lake": "test_data_lake/",
                "logs": "test_logs/"
            },
            "api_keys": {
                "ibm_watsonx": "test-key"
            }
        }

    def test_orchestrator_initializes_crawler_not_none(self, mock_config):
        """Verify orchestrator initializes crawler (no longer None)"""
        # Act
        orchestrator = PipelineOrchestrator(mock_config)

        # Assert
        assert orchestrator.crawler is not None, "Crawler should be initialized, not None"

    def test_orchestrator_crawler_is_crawler_adapter(self, mock_config):
        """Verify orchestrator uses CrawlerAdapter instance"""
        # Act
        orchestrator = PipelineOrchestrator(mock_config)

        # Assert
        assert isinstance(orchestrator.crawler, CrawlerAdapter), \
            "Crawler should be CrawlerAdapter instance"

    def test_orchestrator_crawler_has_crawl_company_method(self, mock_config):
        """Verify crawler exposes crawl_company() method expected by orchestrator"""
        # Act
        orchestrator = PipelineOrchestrator(mock_config)

        # Assert
        assert hasattr(orchestrator.crawler, 'crawl_company'), \
            "Crawler must have crawl_company method"
        assert callable(orchestrator.crawler.crawl_company), \
            "crawl_company must be callable"

    @patch('apps.pipeline_orchestrator.MultiSourceCrawler')
    def test_orchestrator_initializes_multisource_crawler(self, mock_msc_class, mock_config):
        """Verify orchestrator creates MultiSourceCrawler with correct config"""
        # Arrange
        mock_crawler_instance = Mock()
        mock_msc_class.return_value = mock_crawler_instance

        # Act
        orchestrator = PipelineOrchestrator(mock_config)

        # Assert
        mock_msc_class.assert_called_once()
        # Verify adapter wraps the crawler instance
        assert orchestrator.crawler._crawler is mock_crawler_instance

    def test_orchestrator_crawler_signature_matches_expected(self, mock_config):
        """Verify crawl_company signature: (company_cik: str, fiscal_year: int) → dict"""
        from inspect import signature

        # Act
        orchestrator = PipelineOrchestrator(mock_config)
        sig = signature(orchestrator.crawler.crawl_company)

        # Assert
        assert 'company_cik' in sig.parameters, "Must accept company_cik parameter"
        assert 'fiscal_year' in sig.parameters, "Must accept fiscal_year parameter"
        assert sig.parameters['company_cik'].annotation == str, "company_cik must be str"
        assert sig.parameters['fiscal_year'].annotation == int, "fiscal_year must be int"
        assert sig.return_annotation == dict, "Must return dict"

    def test_orchestrator_handles_crawler_initialization_failure(self):
        """Verify orchestrator fails gracefully if crawler init fails"""
        # This test verifies orchestrator doesn't swallow initialization errors

        with patch('apps.pipeline_orchestrator.MultiSourceCrawler') as mock_msc:
            mock_msc.side_effect = Exception("Failed to load data source registry")

            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                PipelineOrchestrator({"paths": {}, "api_keys": {}})

            assert "data source registry" in str(exc_info.value).lower()

    @patch('apps.pipeline_orchestrator.MultiSourceCrawler')
    def test_phase2_crawl_uses_adapter_interface(self, mock_msc_class, mock_config):
        """Verify _phase2_crawl calls crawler.crawl_company with correct args"""
        # Arrange
        mock_crawler_instance = Mock()
        mock_crawler_instance.search_company_reports.return_value = {
            "sec_edgar": [{
                "company_name": "Microsoft Corporation",
                "content": "10-K content",
                "source": "sec_edgar",
                "timestamp": "2024-01-01T00:00:00Z",
                "sha256": "abc123"
            }]
        }
        mock_msc_class.return_value = mock_crawler_instance

        orchestrator = PipelineOrchestrator(mock_config)

        # Mock the adapter's crawl_company method to return expected format
        mock_report = {
            "company_name": "Microsoft Corporation",
            "content": "10-K content",
            "source": "sec_edgar",
            "timestamp": "2024-01-01T00:00:00Z",
            "sha256": "abc123"
        }
        orchestrator.crawler.crawl_company = Mock(return_value=mock_report)

        # Act
        result = orchestrator._phase2_crawl(company_cik="0000789019", fiscal_year=2024)

        # Assert
        orchestrator.crawler.crawl_company.assert_called_once_with("0000789019", 2024)
        assert result == mock_report

    def test_orchestrator_crawler_failure_path_raises_pipeline_error(self, mock_config):
        """Verify orchestrator raises PipelineError when crawler.crawl_company fails"""
        from apps.pipeline_orchestrator import PipelineError

        # Arrange
        orchestrator = PipelineOrchestrator(mock_config)
        orchestrator.crawler.crawl_company = Mock(side_effect=Exception("Network timeout"))

        # Act & Assert
        with pytest.raises(PipelineError) as exc_info:
            orchestrator._phase2_crawl("0000789019", 2024)

        assert exc_info.value.phase == "Phase 2"
        assert "Network timeout" in str(exc_info.value)

    def test_orchestrator_crawler_empty_report_raises_pipeline_error(self, mock_config):
        """Verify orchestrator raises PipelineError when crawler returns empty report"""
        from apps.pipeline_orchestrator import PipelineError

        # Arrange
        orchestrator = PipelineOrchestrator(mock_config)
        orchestrator.crawler.crawl_company = Mock(return_value={})  # Empty dict

        # Act & Assert
        with pytest.raises(PipelineError) as exc_info:
            orchestrator._phase2_crawl("0000789019", 2024)

        assert exc_info.value.phase == "Phase 2"
        assert "empty report" in str(exc_info.value).lower()

    @pytest.mark.parametrize("cik,year", [
        ("0000320193", 2024),  # Apple
        ("0000789019", 2023),  # Microsoft
        ("0001018724", 2022),  # Amazon
    ])
    @patch('apps.pipeline_orchestrator.MultiSourceCrawler')
    def test_orchestrator_crawler_works_for_multiple_companies(self, mock_msc_class, mock_config, cik, year):
        """Verify orchestrator crawler handles different companies"""
        # Arrange
        mock_crawler_instance = Mock()
        mock_msc_class.return_value = mock_crawler_instance

        orchestrator = PipelineOrchestrator(mock_config)
        orchestrator.crawler.crawl_company = Mock(return_value={
            "company_name": "Test Company",
            "content": "Report content",
            "source": "sec_edgar"
        })

        # Act
        result = orchestrator._phase2_crawl(cik, year)

        # Assert
        orchestrator.crawler.crawl_company.assert_called_once_with(cik, year)
        assert result["company_name"] == "Test Company"
