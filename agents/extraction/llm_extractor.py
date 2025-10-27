"""
LLM Extractor - Phase 3B

Extracts ESG metrics from unstructured data (PDF) using IBM watsonx.ai LLM.

Author: Scientific Coding Agent v13.8-MEA
Date: 2025-10-24
"""

import os
import json
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
from ibm_watsonx_ai import Credentials, APIClient
from ibm_watsonx_ai.foundation_models import ModelInference

from agents.extraction.pdf_text_extractor import PDFTextExtractor
from libs.models.esg_metrics import ESGMetrics
from libs.contracts.extraction_contracts import (
    ExtractionResult,
    ExtractionQuality,
    ExtractionError
)
from libs.contracts.ingestion_contracts import CompanyReport


class LLMExtractor:
    """Extracts ESG metrics from unstructured data using IBM watsonx.ai.

    Uses llama-3-3-70b-instruct model with greedy decoding for deterministic outputs.
    Implements response caching for reproducible testing.
    """

    def __init__(
        self,
        project_id: str,
        api_key: str,
        model_id: str = "meta-llama/llama-3-3-70b-instruct",
        use_cache: bool = True,
        cache_path: str = "test_data/llm_cache"
    ):
        """Initialize LLM extractor with IBM watsonx.ai credentials.

        Args:
            project_id: IBM Cloud project ID
            api_key: IAM API key
            model_id: watsonx.ai model ID
            use_cache: Whether to cache/replay responses (for deterministic tests)
            cache_path: Path to cache directory
        """
        self.project_id = project_id
        self.model_id = model_id
        self.use_cache = use_cache
        self.cache_path = cache_path

        # Initialize watsonx.ai client
        credentials = Credentials(
            url="https://us-south.ml.cloud.ibm.com",
            api_key=api_key
        )
        self.client = APIClient(credentials)
        self.model = ModelInference(
            model_id=model_id,
            api_client=self.client,
            project_id=project_id
        )

        self.pdf_extractor = PDFTextExtractor()
        self.errors: List[ExtractionError] = []

    def extract(self, report: CompanyReport) -> ExtractionResult:
        """Extract ESG metrics from PDF report using LLM.

        Workflow:
        1. Extract text from PDF using PyMuPDF
        2. Construct LLM prompt with text + JSON schema
        3. Call watsonx.ai API with retry logic (or use cache)
        4. Parse LLM JSON response into ESGMetrics
        5. Assess extraction quality

        Args:
            report: CompanyReport with local_path to PDF

        Returns:
            ExtractionResult with metrics, quality, and errors

        Raises:
            ValueError: If report.local_path is None
        """
        self.errors = []

        if report.local_path is None:
            raise ValueError("CompanyReport.local_path is None")

        # Step 1: Extract text from PDF
        try:
            text = self.pdf_extractor.extract_text(report.local_path)
        except Exception as e:
            self.errors.append(ExtractionError(
                field_name=None,
                error_type=type(e).__name__,
                message=f"PDF text extraction failed: {e}",
                severity="error"
            ))
            return ExtractionResult(
                metrics=None,
                quality=ExtractionQuality(0.0, 0.0, 0.0),
                errors=self.errors
            )

        # Step 2: Construct prompt
        prompt = self._construct_prompt(
            company_name=report.company.name,
            fiscal_year=report.year,
            text=text
        )

        # Step 3: Call LLM with retry and caching
        cache_key = f"{report.company.cik}_{report.year}"
        try:
            response_json = self._call_llm_with_cache(
                prompt=prompt,
                cache_key=cache_key
            )
        except Exception as e:
            self.errors.append(ExtractionError(
                field_name=None,
                error_type=type(e).__name__,
                message=f"LLM API call failed: {e}",
                severity="error"
            ))
            return ExtractionResult(
                metrics=None,
                quality=ExtractionQuality(0.0, 0.0, 0.0),
                errors=self.errors
            )

        # Step 4: Parse response into ESGMetrics
        metrics = self._parse_llm_response(response_json, report)

        # Step 5: Calculate quality
        quality = self._calculate_quality(metrics)

        return ExtractionResult(
            metrics=metrics,
            quality=quality,
            errors=self.errors
        )

    def _construct_prompt(self, company_name: str, fiscal_year: int, text: str) -> str:
        """Construct extraction prompt with JSON schema.

        Args:
            company_name: Company name
            fiscal_year: Fiscal year
            text: PDF text content

        Returns:
            Prompt string for LLM
        """
        # Truncate text to fit model context window (~12,000 chars = ~3,000 tokens)
        max_chars = 12000
        truncated_text = text[:max_chars]

        prompt = f"""Extract ESG (Environmental, Social, Governance) metrics from the following sustainability report for {company_name} (fiscal year {fiscal_year}).

Report Text:
{truncated_text}

Extract the following metrics and return as JSON. If a metric is not found in the text, use null.

Metrics to extract:
- scope1_emissions (number): Scope 1 greenhouse gas emissions in metric tons CO2e
- scope2_emissions (number): Scope 2 greenhouse gas emissions in metric tons CO2e
- scope3_emissions (number): Scope 3 greenhouse gas emissions in metric tons CO2e
- renewable_energy_pct (number): Percentage of renewable energy used (0-100)
- water_withdrawal (number): Total water withdrawal in cubic meters
- waste_recycled_pct (number): Percentage of waste recycled (0-100)
- women_in_workforce_pct (number): Percentage of women in workforce (0-100)
- employee_turnover_pct (number): Employee turnover rate as percentage (0-100)

Return ONLY valid JSON in this exact format (no explanations or text outside JSON):
{{
  "scope1_emissions": <number or null>,
  "scope2_emissions": <number or null>,
  "scope3_emissions": <number or null>,
  "renewable_energy_pct": <number or null>,
  "water_withdrawal": <number or null>,
  "waste_recycled_pct": <number or null>,
  "women_in_workforce_pct": <number or null>,
  "employee_turnover_pct": <number or null>
}}

If a metric is not found in the text, use null. Do NOT fabricate values."""

        return prompt

    def _call_llm_with_cache(self, prompt: str, cache_key: str) -> Dict[str, Any]:
        """Call watsonx.ai LLM with caching for deterministic tests.

        Args:
            prompt: Extraction prompt
            cache_key: Unique key for caching (e.g., "cik_year")

        Returns:
            Parsed JSON response from LLM

        Raises:
            Exception: If API call fails after retries
        """
        cache_file = os.path.join(self.cache_path, f"{cache_key}.json")

        # Check cache first
        if self.use_cache and os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
                return cached["response"]

        # Call LLM with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.model.generate(
                    prompt=prompt,
                    params={
                        "decoding_method": "greedy",  # Deterministic
                        "max_new_tokens": 500,
                        "temperature": 0.0,  # No randomness
                        "stop_sequences": ["}"]  # Stop after JSON
                    }
                )

                # Extract generated text
                generated_text = response["results"][0]["generated_text"]

                # Parse JSON from response
                # Find JSON object in response
                start_idx = generated_text.find("{")
                if start_idx == -1:
                    raise ValueError("No JSON object found in LLM response")

                end_idx = generated_text.rfind("}") + 1
                if end_idx == 0:
                    raise ValueError("Incomplete JSON object in LLM response")

                json_str = generated_text[start_idx:end_idx]
                response_json = json.loads(json_str)

                # Cache response
                if self.use_cache:
                    os.makedirs(self.cache_path, exist_ok=True)
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump({
                            "cache_key": cache_key,
                            "model_id": self.model_id,
                            "timestamp": datetime.utcnow().isoformat(),
                            "response": response_json
                        }, f, indent=2)

                return response_json

            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff

    def _parse_llm_response(
        self,
        response_json: Dict[str, Any],
        report: CompanyReport
    ) -> Optional[ESGMetrics]:
        """Parse LLM JSON response into ESGMetrics.

        Args:
            response_json: LLM response as dict
            report: Original CompanyReport

        Returns:
            ESGMetrics instance or None if parsing fails
        """
        try:
            # Map LLM response to ESGMetrics fields
            metrics_dict = {
                "company_name": report.company.name,
                "cik": report.company.cik,
                "fiscal_year": report.year,
                "extraction_method": "llm",
                "data_source": "sustainability_report",
                "scope1_emissions": response_json.get("scope1_emissions"),
                "scope2_emissions": response_json.get("scope2_emissions"),
                "scope3_emissions": response_json.get("scope3_emissions"),
                "renewable_energy_pct": response_json.get("renewable_energy_pct"),
                "water_withdrawal": response_json.get("water_withdrawal"),
                "waste_recycled_pct": response_json.get("waste_recycled_pct"),
                "women_in_workforce_pct": response_json.get("women_in_workforce_pct"),
                "employee_turnover_pct": response_json.get("employee_turnover_pct"),
            }

            metrics = ESGMetrics(**metrics_dict)
            return metrics

        except Exception as e:
            self.errors.append(ExtractionError(
                field_name=None,
                error_type=type(e).__name__,
                message=f"Failed to parse LLM response: {e}",
                severity="error"
            ))
            return None

    def _calculate_quality(self, metrics: Optional[ESGMetrics]) -> ExtractionQuality:
        """Calculate extraction quality metrics.

        Args:
            metrics: Extracted ESGMetrics or None

        Returns:
            ExtractionQuality with completeness, correctness, validity scores
        """
        if metrics is None:
            return ExtractionQuality(0.0, 0.0, 0.0)

        # Count non-null ESG fields
        esg_fields = [
            "scope1_emissions", "scope2_emissions", "scope3_emissions",
            "renewable_energy_pct", "water_withdrawal", "waste_recycled_pct",
            "women_in_workforce_pct", "employee_turnover_pct"
        ]

        non_null_count = sum(
            1 for field in esg_fields
            if getattr(metrics, field) is not None
        )

        field_completeness = non_null_count / len(esg_fields)

        # Assume LLM responses are type-correct (Pydantic validated)
        type_correctness = 1.0

        # Value validity: assume valid (Pydantic validates ranges)
        value_validity = 1.0

        return ExtractionQuality(
            field_completeness=field_completeness,
            type_correctness=type_correctness,
            value_validity=value_validity
        )
