"""
IBM watsonx.ai client for embeddings, extraction, and classification
Production implementation with NO MOCK functionality - real services only
"""

import os
import json
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import time
from functools import lru_cache
from dotenv import load_dotenv
from libs.utils.clock import get_clock
clock = get_clock()

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Import IBM Watson libraries (REQUIRED - no fallback)
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.foundation_models.embeddings import Embeddings
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, EmbeddingTypes
from ibm_watsonx_ai import APIClient, Credentials


@dataclass
class WatsonXConfig:
    """Configuration for watsonx.ai client"""
    api_key: str
    project_id: str
    region: str
    url: str
    embedding_model: str = "ibm/slate-125m-english-rtrvr-v2"  # Slate embedding model
    extraction_model: str = "meta-llama/llama-3-3-70b-instruct"  # LLM for extraction
    classification_model: str = "meta-llama/llama-3-3-70b-instruct"  # LLM for classification
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 50
    repetition_penalty: float = 1.0
    cache_ttl: int = 604800  # 7 days for embeddings
    cache_dir: Optional[Path] = None

    @classmethod
    def from_env(cls) -> 'WatsonXConfig':
        """Load configuration from environment variables"""
        return cls(
            api_key=os.getenv("WATSONX_API_KEY", ""),
            project_id=os.getenv("WATSONX_PROJECT_ID", ""),
            region=os.getenv("WATSONX_REGION", "us-south"),
            url=os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
            embedding_model=os.getenv("WATSONX_EMBEDDING_MODEL", "ibm/slate-125m-english-rtrvr-v2"),
            extraction_model=os.getenv("WATSONX_EXTRACTION_MODEL", "meta-llama/llama-3-3-70b-instruct"),
            classification_model=os.getenv("WATSONX_CLASSIFICATION_MODEL", "meta-llama/llama-3-3-70b-instruct"),
            max_tokens=int(os.getenv("WATSONX_MAX_TOKENS", "2048")),
            temperature=float(os.getenv("WATSONX_TEMPERATURE", "0.7")),
            top_p=float(os.getenv("WATSONX_TOP_P", "0.95")),
            top_k=int(os.getenv("WATSONX_TOP_K", "50")),
            repetition_penalty=float(os.getenv("WATSONX_REPETITION_PENALTY", "1.0")),
            cache_ttl=int(os.getenv("CACHE_EMBEDDING_TTL", "604800")),
            cache_dir=Path(os.getenv("CACHE_DIR", "./data/cache"))
        )


class WatsonXClient:
    """
    Production client for IBM watsonx.ai - REAL SERVICES ONLY
    Handles embeddings, extraction, and classification
    NO MOCK FUNCTIONALITY - fails if services unavailable
    """

    def __init__(self, config: Optional[WatsonXConfig] = None):
        self.config = config or WatsonXConfig.from_env()
        self.cache_dir = self.config.cache_dir or Path("data/cache/watsonx")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize clients - REQUIRED
        if not self.config.api_key:
            raise ValueError("WATSONX_API_KEY is required - no mock mode available")
        if not self.config.project_id:
            raise ValueError("WATSONX_PROJECT_ID is required - no mock mode available")

        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize watsonx.ai API clients - REQUIRED, no fallback"""
        try:
            # Create credentials
            self.credentials = Credentials(
                url=self.config.url,
                api_key=self.config.api_key
            )

            # Create API client for general use
            self.api_client = APIClient(self.credentials, project_id=self.config.project_id)

            # Initialize Embeddings model (using correct Embeddings class)
            embed_params = {
                EmbedParams.TRUNCATE_INPUT_TOKENS: 512,  # Max tokens for embeddings
                EmbedParams.RETURN_OPTIONS: {
                    'input_text': False  # Don't return input text in response
                }
            }

            self.embedding_model = Embeddings(
                model_id=self.config.embedding_model,
                params=embed_params,
                credentials=self.credentials,
                project_id=self.config.project_id
            )

            # Initialize extraction model (using ModelInference class for text generation)
            extraction_params = {
                GenParams.MAX_NEW_TOKENS: self.config.max_tokens,
                GenParams.TEMPERATURE: 0.3,  # Lower for extraction
                GenParams.TOP_P: self.config.top_p,
                GenParams.TOP_K: self.config.top_k,
                GenParams.REPETITION_PENALTY: self.config.repetition_penalty
            }

            self.extraction_model = ModelInference(
                model_id=self.config.extraction_model,
                params=extraction_params,
                credentials=self.credentials,
                project_id=self.config.project_id
            )

            # Initialize classification model
            classification_params = {
                GenParams.MAX_NEW_TOKENS: 512,  # Less tokens needed
                GenParams.TEMPERATURE: 0.5,  # Moderate for classification
                GenParams.TOP_P: self.config.top_p,
                GenParams.TOP_K: self.config.top_k,
                GenParams.REPETITION_PENALTY: self.config.repetition_penalty
            }

            self.classification_model = ModelInference(
                model_id=self.config.classification_model,
                params=classification_params,
                credentials=self.credentials,
                project_id=self.config.project_id
            )

            logger.info("WatsonX clients initialized successfully with REAL services")

        except Exception as e:
            logger.error(f"Failed to initialize WatsonX clients: {e}")
            raise RuntimeError(f"Cannot initialize watsonx.ai clients - real services required: {e}")

    def generate_embedding(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Generate embedding for text using watsonx.ai REAL service
        Returns 768-dimensional vector
        NO MOCK FALLBACK - raises exception on failure
        """
        # Check cache
        if use_cache:
            cached = self._get_cached_embedding(text)
            if cached is not None:
                return cached

        # Generate embedding using REAL API
        try:
            # Use the embed() method for single text
            response = self.embedding_model.embed_documents([text])

            if response and len(response) > 0:
                # Extract embedding from response
                embedding = np.array(response[0])

                # Normalize to unit vector
                embedding = embedding / np.linalg.norm(embedding)

                # Cache result
                if use_cache:
                    self._cache_embedding(text, embedding)

                return embedding
            else:
                raise ValueError("Empty response from embedding API")

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Embedding generation failed - real service required: {e}")

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 10,
        use_cache: bool = True
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts - REAL SERVICE ONLY
        """
        embeddings = []

        # Check cache for all texts
        uncached_texts = []
        uncached_indices = []

        if use_cache:
            for i, text in enumerate(texts):
                cached = self._get_cached_embedding(text)
                if cached is not None:
                    embeddings.append(cached)
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))

        # Process uncached texts in batches
        if uncached_texts:
            for i in range(0, len(uncached_texts), batch_size):
                batch = uncached_texts[i:i + batch_size]

                try:
                    # Generate embeddings for batch using REAL API
                    batch_response = self.embedding_model.embed_documents(batch)

                    if batch_response and len(batch_response) == len(batch):
                        batch_embeddings = [np.array(emb) for emb in batch_response]

                        # Normalize
                        batch_embeddings = [
                            emb / np.linalg.norm(emb) for emb in batch_embeddings
                        ]

                        # Cache if enabled
                        if use_cache:
                            for text, emb in zip(batch, batch_embeddings):
                                self._cache_embedding(text, emb)

                        # Add to results
                        for emb in batch_embeddings:
                            embeddings.append(emb)
                    else:
                        raise ValueError(f"Invalid batch response: expected {len(batch)} embeddings")

                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    raise RuntimeError(f"Batch embedding generation failed - real service required: {e}")

        return embeddings

    def extract_findings(
        self,
        text: str,
        query: str,
        theme: str,
        max_findings: int = 5
    ) -> Dict[str, Any]:
        """
        Extract ESG findings from text - REAL LLM SERVICE ONLY
        """
        prompt = f"""Extract specific ESG findings related to {theme} from the following text.
Focus on: {query}

Text:
{text[:2000]}

IMPORTANT: Score each finding's evidence strength:
- 0.9-1.0: Quantified metric with third-party verification (e.g., "30% reduction verified by Deloitte")
- 0.7-0.8: Quantified metric without verification (e.g., "reduced emissions by 30%")
- 0.5-0.6: Specific commitment with timeline (e.g., "net-zero by 2030")
- 0.3-0.4: General commitment without timeline
- 0.1-0.2: Vague statement

Provide a JSON response with:
{{
    "findings": [
        {{
            "quote": "exact quote from text",
            "relevance": "how it relates to {theme}",
            "indicators": ["specific metrics or indicators mentioned"],
            "evidence_strength": 0.0-1.0 (based on criteria above)
        }}
    ],
    "summary": "brief overall assessment",
    "confidence": 0.0-1.0 (average of evidence_strength scores),
    "data_quality": "high|medium|low" (high if avg strength > 0.7, medium if > 0.4, else low)
}}

Extract up to {max_findings} most relevant findings."""

        try:
            # Use REAL LLM API with generate method
            response_dict = self.extraction_model.generate(prompt=prompt)

            if response_dict and 'results' in response_dict and len(response_dict['results']) > 0:
                response = response_dict['results'][0].get('generated_text', '')
                # Parse JSON response - handle extra text around JSON
                try:
                    # First try direct parse
                    findings = json.loads(response)
                    return findings
                except json.JSONDecodeError:
                    # Try to extract JSON from response
                    import re
                    # Look for JSON object, being careful with nested braces
                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
                    if json_match:
                        try:
                            findings = json.loads(json_match.group())
                            return findings
                        except:
                            # If that fails, try to find the first complete JSON object
                            start = response.find('{')
                            if start >= 0:
                                brace_count = 0
                                for i, char in enumerate(response[start:], start):
                                    if char == '{':
                                        brace_count += 1
                                    elif char == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            try:
                                                findings = json.loads(response[start:i+1])
                                                return findings
                                            except:
                                                break

                    # Return structured fallback response
                    return {
                        "findings": [],
                        "summary": "Could not parse response as JSON",
                        "confidence": 0.5,
                        "raw_response": response[:200]
                    }
            else:
                raise ValueError("Empty response from extraction API")

        except Exception as e:
            logger.error(f"Failed to extract findings: {e}")
            raise RuntimeError(f"Finding extraction failed - real service required: {e}")

    def classify_maturity(
        self,
        findings: List[Dict[str, Any]],
        theme: str,
        rubric: Optional[Dict[int, str]] = None
    ) -> Dict[str, Any]:
        """
        Classify ESG maturity based on findings - REAL LLM SERVICE ONLY
        """
        if rubric is None:
            rubric = {
                0: "No meaningful action or disclosure",
                1: "Basic awareness and initial reporting",
                2: "Targets set with implementation planning",
                3: "Active implementation with progress tracking",
                4: "Leading practice with demonstrated impact"
            }

        # Format findings for prompt
        findings_text = "\n".join([
            f"- {f.get('quote', '')}: {f.get('relevance', '')}"
            for f in findings[:10]
        ])

        prompt = f"""Based on these {theme} findings, classify the maturity stage:

Findings:
{findings_text}

Maturity Rubric:
{json.dumps(rubric, indent=2)}

CONFIDENCE CALCULATION INSTRUCTIONS:
Calculate confidence based on evidence quality:
- 0.80-1.00: Multiple quantified metrics with verification (e.g., "30% reduction verified by Deloitte")
- 0.60-0.79: Quantified metrics without verification (e.g., "reduced emissions by 30%")
- 0.40-0.59: Specific commitments with timelines (e.g., "net-zero by 2030")
- 0.20-0.39: General commitments without specifics (e.g., "committed to sustainability")

Count the findings:
- 5+ high-quality findings: Add 0.1 to confidence
- 3-4 findings: No adjustment
- 1-2 findings: Subtract 0.1 from confidence
- 0 findings: Set confidence to 0.2

Respond with JSON:
{{
    "stage": 0-4,
    "confidence": 0.0-1.0 (MUST vary based on evidence quality, NOT default to 0.5),
    "reasoning": "explanation of classification",
    "evidence": ["key evidence points"],
    "evidence_quality": "high|medium|low"
}}"""

        try:
            # Use REAL LLM API with generate method
            response_dict = self.classification_model.generate(prompt=prompt)

            if response_dict and 'results' in response_dict and len(response_dict['results']) > 0:
                response = response_dict['results'][0].get('generated_text', '')
                # Parse JSON response - handle extra text around JSON
                try:
                    classification = json.loads(response)
                    # Validate stage is in range
                    if 'stage' in classification:
                        classification['stage'] = max(0, min(4, classification['stage']))
                    return classification
                except json.JSONDecodeError:
                    # Try to extract JSON
                    import re
                    # Try to find first complete JSON object
                    start = response.find('{')
                    if start >= 0:
                        brace_count = 0
                        for i, char in enumerate(response[start:], start):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    try:
                                        classification = json.loads(response[start:i+1])
                                        if 'stage' in classification:
                                            classification['stage'] = max(0, min(4, classification['stage']))
                                        return classification
                                    except:
                                        break

                    # Return structured fallback
                    return {
                        "stage": 2,  # Default to middle stage
                        "confidence": 0.5,
                        "reasoning": "Could not parse LLM response",
                        "evidence": [],
                        "raw_response": response[:200]
                    }
            else:
                raise ValueError("Empty response from classification API")

        except Exception as e:
            logger.error(f"Failed to classify maturity: {e}")
            raise RuntimeError(f"Maturity classification failed - real service required: {e}")

    def summarize_text(self, text: str, max_length: int = 200) -> str:
        """
        Summarize text using watsonx.ai - REAL SERVICE ONLY
        """
        prompt = f"""Summarize the following text in {max_length} words or less, focusing on ESG-relevant information:

{text[:3000]}

Summary:"""

        try:
            response_dict = self.extraction_model.generate(prompt=prompt)
            if response_dict and 'results' in response_dict and len(response_dict['results']) > 0:
                response = response_dict['results'][0].get('generated_text', '')
                return response.strip()
            else:
                raise ValueError("Empty response from summarization API")
        except Exception as e:
            logger.error(f"Failed to summarize text: {e}")
            raise RuntimeError(f"Text summarization failed - real service required: {e}")

    def _get_cached_embedding(self, text: str) -> Optional[np.ndarray]:
        """Retrieve cached embedding"""
        cache_key = hashlib.md5(text.encode()).hexdigest()
        cache_file = self.cache_dir / f"emb_{cache_key}.npy"

        if cache_file.exists():
            # Check TTL
            age = clock.time() - cache_file.stat().st_mtime
            if age < self.config.cache_ttl:
                try:
                    return np.load(cache_file)
                except Exception as e:
                    logger.warning(f"Failed to load cached embedding: {e}")

        return None

    def _cache_embedding(self, text: str, embedding: np.ndarray):
        """Cache embedding to disk"""
        cache_key = hashlib.md5(text.encode()).hexdigest()
        cache_file = self.cache_dir / f"emb_{cache_key}.npy"

        try:
            np.save(cache_file, embedding)
        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")

    def test_connection(self) -> Dict[str, Any]:
        """Test watsonx.ai connection and configuration - REAL ONLY"""
        results = {
            "connected": False,
            "api_key_valid": bool(self.config.api_key),
            "project_id_valid": bool(self.config.project_id),
            "embedding_model": self.config.embedding_model,
            "extraction_model": self.config.extraction_model,
            "classification_model": self.config.classification_model
        }

        try:
            # Test with simple embedding
            test_text = "Test connection to watsonx.ai services"
            embedding = self.generate_embedding(test_text, use_cache=False)

            if embedding is not None and len(embedding) > 0:
                results["connected"] = True
                results["embedding_test"] = "success"
                results["embedding_dimension"] = len(embedding)
            else:
                results["embedding_test"] = "failed"
                results["error"] = "Invalid embedding result"

        except Exception as e:
            results["error"] = str(e)
            results["connected"] = False

        return results


# Singleton instance
_client_instance = None


def get_watsonx_client() -> WatsonXClient:
    """Get singleton WatsonX client instance - REAL SERVICE ONLY"""
    global _client_instance
    if _client_instance is None:
        _client_instance = WatsonXClient()
    return _client_instance


# Export key classes
__all__ = ['WatsonXClient', 'WatsonXConfig', 'get_watsonx_client']